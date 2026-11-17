def predict_performance(marks, attendance_percentage):
    """Project the next mark from a student's recent marks and attendance."""
    scores = [float(mark) for mark in marks][-5:]
    attendance_percentage = float(attendance_percentage)

    if len(scores) < 2:
        return {
            "predicted_score": None,
            "status": "More marks needed",
            "confidence": "Not enough history",
            "explanation": "Record at least two marks to calculate a trend.",
        }

    count = len(scores)
    mean_x = (count - 1) / 2
    mean_y = sum(scores) / count
    numerator = sum(
        (index - mean_x) * (score - mean_y)
        for index, score in enumerate(scores)
    )
    denominator = sum((index - mean_x) ** 2 for index in range(count))
    slope = numerator / denominator
    estimate = max(0.0, min(100.0, mean_y + slope * (count - mean_x)))
    estimate = round(estimate, 1)

    if estimate < 50 or attendance_percentage < 65:
        status = "At risk"
    elif estimate < 70 or attendance_percentage < 75:
        status = "Needs attention"
    else:
        status = "On track"

    confidence = "Early trend" if count < 4 else "Trend from recent marks"
    explanation = (
        f"Estimate uses the last {count} recorded marks and attendance of "
        f"{attendance_percentage:.1f}%. Treat it as guidance, not a grade."
    )
    return {
        "predicted_score": estimate,
        "status": status,
        "confidence": confidence,
        "explanation": explanation,
    }
