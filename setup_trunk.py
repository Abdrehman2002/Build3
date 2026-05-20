"""
Run this ONCE after LiveKit SIP is running on the Nayatel VM.
It creates the SIP inbound trunk and dispatch rule in LiveKit.

Usage:
    python setup_trunk.py
"""

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

DID_NUMBER     = "+920518850810"   # Nayatel DID in E.164 format


async def main():
    api = LiveKitAPI(url=LIVEKIT_URL, api_key=LIVEKIT_KEY, api_secret=LIVEKIT_SECRET)

    # ── Step 1: Create inbound SIP trunk ──────────────────────────────────────
    print("Creating SIP inbound trunk...")
    trunk = await api.sip.create_sip_inbound_trunk(
        CreateSIPInboundTrunkRequest(
            trunk=SIPInboundTrunkInfo(
                name="Nayatel",
                numbers=[DID_NUMBER],
                # IP-based auth — Nayatel authenticates by source IP
                # No username/password needed
            )
        )
    )
    print(f"  Trunk created: {trunk.sid}")

    # ── Step 2: Create dispatch rule → routes call to Sara ────────────────────
    print("Creating SIP dispatch rule...")
    rule = await api.sip.create_sip_dispatch_rule(
        CreateSIPDispatchRuleRequest(
            rule=SIPDispatchRule(
                dispatch_rule_individual=SIPDispatchRuleIndividual(
                    room_prefix="sip-call-",
                    pin="",                 # no PIN needed
                ),
                trunk_ids=[trunk.sid],
                name="Sara SIP Inbound",
            ),
            agent_name="sara",             # dispatch explicitly to Sara agent
        )
    )
    print(f"  Dispatch rule created: {rule.sid}")
    print()
    print("Done! Sara will now answer calls to 0518850810.")
    print(f"Trunk ID:        {trunk.sid}")
    print(f"Dispatch Rule:   {rule.sid}")

    await api.aclose()


if __name__ == "__main__":
    asyncio.run(main())
