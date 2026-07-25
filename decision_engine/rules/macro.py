def evaluate_macro_environment() -> tuple[float, list[str], list[str]]:
    """
    Evaluates Macroeconomics/Interest Rates (RBI/Fed).
    Weight: 20%
    """
    reasons = []
    rules = []
    
    # Defaults to neutral score for now as Phase 4/macro is skipped/unimplemented
    reasons.append("Macro environment indicators show neutral stance (no policy rate changes detected).")
    rules.append("MACRO_NEUTRAL")
    
    return 50.0, reasons, rules
