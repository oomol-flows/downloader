from dataclasses import dataclass
from typing import Any, Callable, Generic, Generator, TypeVar
from threading import Thread
from queue import Queue


P = TypeVar("P")

@dataclass
class UserEvent(Generic[P]):
  payload: P

@dataclass
class FinishedEvent:
  error: Exception | None

def execute(count: int, handler: Callable[[int, Callable[[P], None]], Any]) -> Generator[P, None, None]:
  event_queue: Queue[UserEvent[P] | FinishedEvent] = Queue(0)
  remain_threads_count = count
  threads: list[Thread] = [
    Thread(
      target=lambda: _execute_handler(id, event_queue, handler),
    )
    for id in range(count)
  ]
  for thread in threads:
    thread.start()

  while True:
    event = event_queue.get()
    if isinstance(event, UserEvent):
      yield event.payload
    elif isinstance(event, FinishedEvent):
      if event.error is not None:
        print(event.error)
      remain_threads_count -= 1
      if remain_threads_count == 0:
        break

  for thread in threads:
    thread.join()

def _execute_handler(
    id: int,
    event_queue: Queue[UserEvent[P] | FinishedEvent],
    handler: Callable[[int, Callable[[P], None]], Any],
  ):
  send: Callable[[P], None] = lambda p: event_queue.put(
    UserEvent(payload=p)
  )
  error: Exception | None = None
  try:
    handler(id, send)
  except Exception as e:
    error = e
  finally:
    event_queue.put(FinishedEvent(error))