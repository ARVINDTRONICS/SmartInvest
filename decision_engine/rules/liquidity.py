def evaluate_liquidity_score(liq_score: float | None) -> tuple[float, list[str], list[str]]:
    """
    Evaluates trading volume liquidity.
    Weight: 10%
    """
    reasons = []
    rules = []

    if liq_score is None:
        reasons.append("Liquidity score is unavailable; neutral assumed.")
        rules.append("LIQUIDITY_UNKNOWN")
        return 50.0, reasons, rules

    if liq_score >= 1.2:
        reasons.append(f"Volume liquidity score is elevated at {liq_score:.2f} (>= 1.2), confirming strong asset commitment.")
        rules.append("LIQUIDITY_HIGH")
        return 80.0, reasons, rules
    elif liq_score <= 0.8:
        reasons.append(f"Volume liquidity score is low at {liq_score:.2f} (<= 0.8), indicating weak market participation.")
        rules.append("LIQUIDITY_LOW")
        return 40.0, reasons, rules
    else:
        reasons.append(f"Volume liquidity score is normal ({liq_score:.2f}).")
        rules.append("LIQUIDITY_NORMAL")
        return 50.0, reasons, rules
