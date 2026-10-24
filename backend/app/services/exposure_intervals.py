from datetime import UTC


def merged_duration_ms(events) -> int:
    intervals = []
    for event in events:
        if event.duration_ms is None or event.duration_ms <= 0:
            continue
        start = event.started_at.replace(tzinfo=event.started_at.tzinfo or UTC)
        end = event.ended_at
        if end is None:
            from datetime import timedelta
            end = start + timedelta(milliseconds=event.duration_ms)
        else:
            end = end.replace(tzinfo=end.tzinfo or UTC)
        intervals.append((start, end))
    total = 0
    previous_end = None
    for start, end in sorted(intervals):
        uncovered = max(start, previous_end) if previous_end else start
        if end > uncovered:
            total += int((end - uncovered).total_seconds() * 1000)
        previous_end = max(previous_end, end) if previous_end else end
    return total
