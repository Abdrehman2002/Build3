#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Sara SIP Setup — run this on the Nayatel VM (101.50.85.186)
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "=== Step 1: Adding route to Nayatel SIP registrar ==="
ip route add 10.50.158.85/32 via 172.16.180.1 2>/dev/null && echo "Route added" || echo "Route already exists"

echo ""
echo "=== Step 2: Installing Docker ==="
apt-get update -y -q
apt-get install -y -q docker.io docker-compose python3 python3-pip
systemctl enable docker
systemctl start docker

echo ""
echo "=== Step 3: Creating project directory ==="
mkdir -p /opt/sara-sip
cd /opt/sara-sip

echo ""
echo "=== Step 4: Writing sip.yaml ==="
cat > /opt/sara-sip/sip.yaml << 'EOF'
api_key: 42cd3baa67acb1a56fb272e8199ea07714e095aa
api_secret: c3f83951a178581c221fb9b7d203a89686194d651c9ccf5cec6cd659ebc3869d
ws_url: wss://livekit.vextriaai.com
logging:
  level: info
sip_port: 5060
rtp_port: 10000-20000
EOF

echo ""
echo "=== Step 5: Writing docker-compose.sip.yml ==="
cat > /opt/sara-sip/docker-compose.yml << 'EOF'
version: "3.9"
services:
  sara-sip:
    image: livekit/sip:latest
    container_name: sara-sip
    network_mode: host
    volumes:
      - ./sip.yaml:/etc/sip.yaml
    command: --config /etc/sip.yaml
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

echo ""
echo "=== Step 6: Starting LiveKit SIP ==="
docker-compose up -d
sleep 5
docker ps | grep sara-sip && echo "sara-sip is running" || echo "ERROR: sara-sip failed to start"

echo ""
echo "=== Step 7: Writing SIP trunk setup script ==="
cat > /opt/sara-sip/setup_trunk.py << 'PYEOF'
import asyncio
from livekit.api import LiveKitAPI
from livekit.protocol.sip import (
    CreateSIPInboundTrunkRequest,
    SIPInboundTrunkInfo,
    CreateSIPDispatchRuleRequest,
    SIPDispatchRule,
    SIPDispatchRuleIndividual,
)

LIVEKIT_URL    = "https://livekit.vextriaai.com"
LIVEKIT_KEY    = "42cd3baa67acb1a56fb272e8199ea07714e095aa"
LIVEKIT_SECRET = "c3f83951a178581c221fb9b7d203a89686194d651c9ccf5cec6cd659ebc3869d"
DID_NUMBER     = "+920518850810"

async def main():
    api = LiveKitAPI(url=LIVEKIT_URL, api_key=LIVEKIT_KEY, api_secret=LIVEKIT_SECRET)

    print("Creating SIP inbound trunk...")
    trunk = await api.sip.create_sip_inbound_trunk(
        CreateSIPInboundTrunkRequest(
            trunk=SIPInboundTrunkInfo(
                name="Nayatel",
                numbers=[DID_NUMBER],
            )
        )
    )
    print(f"  Trunk created: {trunk.sid}")

    print("Creating SIP dispatch rule...")
    rule = await api.sip.create_sip_dispatch_rule(
        CreateSIPDispatchRuleRequest(
            rule=SIPDispatchRule(
                dispatch_rule_individual=SIPDispatchRuleIndividual(
                    room_prefix="sip-call-",
                    pin="",
                ),
                trunk_ids=[trunk.sid],
                name="Sara SIP Inbound",
            )
        )
    )
    print(f"  Dispatch rule created: {rule.sid}")
    print()
    print("Done! Trunk ID:", trunk.sid)
    print("Dispatch Rule:", rule.sid)
    await api.aclose()

asyncio.run(main())
PYEOF

echo ""
echo "=== Step 8: Installing Python LiveKit SDK ==="
pip3 install livekit-api -q

echo ""
echo "=== Step 9: Creating SIP trunk and dispatch rule ==="
python3 /opt/sara-sip/setup_trunk.py

echo ""
echo "=========================================="
echo "  SETUP COMPLETE"
echo "  Sara will now answer calls to 0518850810"
echo "  Check logs: docker logs sara-sip -f"
echo "=========================================="
