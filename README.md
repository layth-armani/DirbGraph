# DirbGraph

DirbGraph is a small Python program designed to process and analyze the output of the `dirb` tool.

## Requirements

Install the required dependencies using:
```bash
pip install -r requirements.txt
```

## Usage
1. Run the `dirb` tool to generate a text output file:
   ```bash
   dirb <target_url> <wordlist> -o scan.txt
   ```
2. Use this program to process the `scan.txt` file:
   ```bash
   python parser.py
   ```

## License
This project is open-source and available under the MIT License.