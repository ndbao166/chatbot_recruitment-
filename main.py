import runpy
import sys

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "app.py"]
    runpy.run_module("streamlit", run_name="__main__")
