class TestRunner:
    def __init__(self, name: str = "TestApp"):
        self.name = name

    def run(self):
        print(f"Running {self.name} tests...")

if __name__ == "__main__":
    t = TestRunner()
    t.run()
