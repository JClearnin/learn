from collections import deque

def create_deque() -> deque[int]:
    numbers: deque[int] = deque([1,2,3])
    return numbers

if __name__ == "__main__":
    temp = create_deque()
    print(temp)