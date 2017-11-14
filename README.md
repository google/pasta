# pasta: **P**ython **AST** **A**ugmentation

*This is still a work-in-progress; there is much more to do.*

## Mission
Enable python source code refactoring through modifying the AST.

## Design Goals

* **Symmetry**: Given any input source, it should hold that
  `pasta.dump(pasta.parse(src)) == src`.
* **Mutability**: Any changes made in the AST are reflected in the code
  generated from it.
* **Standardization**: The syntax tree parse by pasta will not introduce new
  nodes or structure that the user must learn.

## Disclaimer

This is not an official Google product.
