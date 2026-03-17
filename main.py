import os

import uvicorn


def main():
    print("Hello from career-tracker!")


if __name__ == "__main__":
    self_filename = os.path.splitext(os.path.basename(__file__))[0]
    uvicorn.run(f"{self_filename}:app", host="127.0.0.1", port=8000, reload=True)
