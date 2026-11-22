import logging

def add_to_queue(queue: list, reading: dict, max_size: int = 100) -> int:
    """Додає показання в чергу. Якщо переповнено — прибирає найстаріше з початку."""
    queue.append(reading)
    dropped = 0
    while len(queue) > max_size:
        queue.pop(0)
        dropped += 1
    return dropped

def is_permanent(status_code: int) -> bool:
    """Помилки 4xx (крім 401) є фатальними — повторювати запит марно."""
    return 400 <= status_code < 500 and status_code != 401

async def flush_queue(queue: list, send_func) -> dict:
    """Надсилає накопичені показання з черги по черзі."""
    result = {"sent": 0, "dropped": 0, "left": 0, "error": None}
    
    while len(queue) > 0:
        reading = queue[0]
        try:
            await send_func(reading)
            queue.pop(0)
            result["sent"] += 1
        except Exception as err:
            status = getattr(err, "status", None)
            if status and is_permanent(status):
                queue.pop(0)
                result["dropped"] += 1
            else:
                result["error"] = str(err)
                break
                
    result["left"] = len(queue)
    return result

flushQueue = flush_queue
