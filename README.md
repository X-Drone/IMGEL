# IMGEL - Integrating Micro Grammar into the Existing Language

IMGEL (Integrating Micro Grammar into the Existing Language) is an experimental tool for extending C++ syntax using micro grammars. He demonstrates how to add support for `async/await` patterns by translating them into standard constructs `std::async` and `std::future'.

## Installation

1. clone repo:
    ```bash
    git clone https://github.com/X-Drone/IMGEL.git
    cd imgel
    ```
2. Make shure you:
    - Installed Python 3.10+
    - Module `peco` located at dependences/peco/

## Usage

1. Test:
    ```bash
    python main.py --test
    ```
2. File convert:
    ```bash
    python main.py -i input.cpp -o output.cpp [-v]
    ```

| Argument      | Description           |
| :-----------: | :-------------------: |
| --test        | Running in test mode  |
| -i, --input   | Input file path       |
| -o, --output  | Output file path      |
| -v, --verbose | Printing AST to debug |
