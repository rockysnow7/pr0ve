from sys import argv
from rich import print
from parser import parser, transformer


with open(argv[1]) as f:
    text = f.read()

tree = parser.parse(text)
if transformer.is_correct:
    print(f"[bold green]The proof is valid.[/bold green]")
else:
    print(f"[bold red]The proof is invalid.[/bold red]")