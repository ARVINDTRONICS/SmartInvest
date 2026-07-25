def evaluate_volatility_vix(vix_value: float | None) -> tuple[float, list[str], list[str]]:
    """
    Evaluates volatility fear index (VIX).
    Weight: 10%
    """
    reasons = []
    rules = []

    if vix_value is None:
        reasons.append("VIX volatility index value is unavailable; neutral assumed.")
        rules.append("VIX_UNKNOWN")
        return 50.0, reasons, rules

    if vix_value >= 20.0:
        # High VIX = High Fear = Opportunistic Time to Buy (Value Investing)
        reasons.append(f"VIX is high at {vix_value:.2f} (>= 20), indicating elevated market fear and prime buying conditions.")
        rules.append("VIX_HIGH")
        return 90.0, reasons, rules
    elif vix_value <= 12.0:
        # Low VIX = High Complacency = Sub-optimal Buy
        reasons.append(f"VIX is low at {vix_value:.2f} (<= 12), indicating market complacency.")
        rules.append("VIX_LOW")
        return 40.0, reasons, rules
    else:
        # Moderate VIX
        reasons.append(f"VIX is at moderate levels ({vix_value:.2f}).")
        rules.append("VIX_MODERATE")
        return 60.0, reasons, rules
