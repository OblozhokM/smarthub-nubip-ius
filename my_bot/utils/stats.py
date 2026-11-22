def calc_stats(records: list):
    if not records:
        return None
    
    total_sum = 0.0
    min_val = records[0].get("hours", 0.0)
    max_val = records[0].get("hours", 0.0)
    
    for rec in records:
        val = rec.get("hours", 0.0)
        total_sum += val
        if val < min_val:
            min_val = val
        if val > max_val:
            max_val = val
            
    return {
        "count": len(records),
        "min": min_val,
        "max": max_val,
        "avg": total_sum / len(records)
    }

def group_by_table(records: list):
    groups = {}
    for rec in records:
        t_num = f"Стіл №{rec.get('tableNum')}"
        if t_num not in groups:
            groups[t_num] = []
        groups[t_num].append(rec)
    return groups

def top_values(records: list, count: int):
    rest = records.copy()
    result = []
    
    while len(result) < count and len(rest) > 0:
        max_idx = 0
        for i in range(1, len(rest)):
            if rest[i].get("hours", 0) > rest[max_idx].get("hours", 0):
                max_idx = i
        result.append(rest[max_idx])
        rest.pop(max_idx)
        
    return result