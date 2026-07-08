def main():
    print("Hello from py-core-api!")


def add(a: int, b: int) -> int:
    return a + b


if __name__ == "__main__":
    main()
    result = add(2, 5)
    print(result)
