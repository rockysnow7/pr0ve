from lark import Lark, Transformer
from rich.console import Console
from rich.theme import Theme


console = Console(theme=Theme({
    "correct": "green",
    "incorrect": "red",
    "valid": "bold green",
    "invalid": "bold red",
    "warning": "yellow",
    "info": "bold cyan",
    "debug": "bold magenta",
}))
print = console.print


class LangObject:
    ...

class LangVariable(LangObject):
    def __init__(self, symbol):
        self.symbol = symbol

    def __repr__(self) -> str:
        return f"[italic]{self.symbol}[/italic]"

    def __eq__(self, o: LangObject) -> bool:
        o = simplify(o)        
        if type(o) is LangVariable:
            return self.symbol == o.symbol

        return False
    
    def __hash__(self) -> int:
        return hash(self.__repr__())

class LangExpression(LangObject):
    def __eq__(self, o: LangObject) -> bool:
        if self.__repr__() == o.__repr__():
            return True

        try:
            return simplify(self) == simplify(o)
        except RecursionError:
            return False
    
    def __hash__(self) -> int:
        return hash(self.__repr__())

class LangNot(LangExpression):
    def __init__(self, expr):
        self.symbol = "¬"
        self.expr = expr

    def __repr__(self) -> str:
        return f"{self.symbol}{self.expr}"
    
    def __eq__(self, o: LangObject) -> bool:
        o = simplify(o)        
        if type(o) is LangNot:
            return self.expr == o.expr

        return False
    
    def __hash__(self) -> int:
        return hash(self.__repr__())

class LangAnd(LangExpression):
    def __init__(self, left: LangObject, right: LangObject):
        self.symbol = "&"
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"({self.left} {self.symbol} {self.right})"
    
    def __eq__(self, o: LangObject) -> bool:
        o = simplify(o)        
        if type(o) is LangAnd:
            return self.left == o.left and self.right == o.right or self.left == o.right and self.right == o.left # A & B == A & B, A & B == B & A

        return False
    
    def __hash__(self) -> int:
        return hash(self.__repr__())

class LangImplies(LangExpression):
    def __init__(self, left: LangObject, right: LangObject):
        self.symbol = "->"
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"({self.left} {self.symbol} {self.right})"
    
    def __hash__(self) -> int:
        return hash(self.__repr__())

class LangOr(LangExpression):
    def __init__(self, left: LangObject, right: LangObject):
        self.symbol = "|"
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"({self.left} {self.symbol} {self.right})"
    
    def __eq__(self, o: LangObject) -> bool:
        o = simplify(o)        
        if type(o) is LangOr:
            return self.left == o.left and self.right == o.right or self.left == o.right and self.right == o.left # A | B == A | B, A | B == B | A

        return False
    
    def __hash__(self) -> int:
        return hash(self.__repr__())


def simplify(expr) -> LangObject:
    if type(expr) is LangNot:
        expr = LangNot(simplify(expr.expr))
    elif type(expr) is not LangVariable:
        expr = expr.__class__(simplify(expr.left), simplify(expr.right))

    if type(expr) is LangAnd and expr.left == expr.right: # `A & A` = `A`
        return expr.left
    
    if type(expr) is LangOr and expr.left == expr.right: # `A | A` = `A`
        return expr.left

    if type(expr) is LangNot and type(expr.expr) is LangNot: # `¬¬A` = `A`
        return simplify(expr.expr.expr)
    
    if type(expr) is LangNot and type(expr.expr) is LangAnd: # `¬(A & B)` = `¬A | ¬B`
        return simplify(LangOr(LangNot(expr.expr.left), LangNot(expr.expr.right)))
    
    if type(expr) is LangNot and type(expr.expr) is LangOr: # `¬(A | B)` = `¬A & ¬B`
        return simplify(LangAnd(LangNot(expr.expr.left), LangNot(expr.expr.right)))
    
    return expr

def infer(expr) -> list[LangObject]:
    inferences = [expr]

    if type(expr) is LangAnd:
        inferences.append(expr.left)
        inferences.append(expr.right)

    elif type(expr) is LangImplies:
        inferences.append(LangOr(LangNot(expr.left), expr.right))

    elif type(expr) is LangOr:
        inferences.append(LangImplies(LangNot(expr.left), expr.right))
        inferences.append(LangImplies(LangNot(expr.right), expr.left))

    return inferences


class LangTransformer(Transformer):
    def __init__(self):
        self.is_correct = True
        self.truths = []
        self.record = {}

    def infer_all(self):
        while True:
            truths_copy = self.truths.copy()

            changed = False
            for expr in self.truths:
                inferences = [simplify(i) for i in infer(expr)]
                for i in inferences:
                    if i not in self.truths:
                        truths_copy.append(i)
                        changed = True
            
            if not changed:
                break

            self.truths = truths_copy
        
        changed = False
        #print(f"[debug]{self.truths=}[/]")
        for expr in self.truths:
            if type(expr) is LangImplies and expr.left in self.truths and expr.right not in self.truths:
                self.truths.append(expr.right)
                changed = True
            
        if changed:
            self.infer_all()

    def premise_stmt(self, args):
        truths_copy = self.truths.copy()

        name, expr = args
        name = int(name.value[1:-1])

        if expr not in self.truths:            
            inferences = [simplify(i) for i in infer(expr)]
            negated_inferences = [simplify(LangNot(c)) for c in inferences]

            found = False
            for i in negated_inferences:
                if i in self.truths:
                    found = True
                    break
            
            if found:
                print(f"[incorrect][bold]P{name}.[/] {expr}")
                print(f"\t[info]This entails[/]\t{inferences}.")

                self.is_correct = False
                if simplify(i) in self.record:
                    print(f"\t[incorrect][bold]P{name}[/bold] is a contradiction of[/] {i} [incorrect]from [bold]{self.record[simplify(i)]}[/bold].[/incorrect]")
                else:
                    print(f"\t[incorrect][bold]P{name}[/bold] is a contradiction of[/] {i}[incorrect].[/incorrect]")

            if self.is_correct:
                print(f"[correct][bold]P{name}.[/] {expr}")
                print(f"\t[info]This entails[/]\t{inferences}.")
                
                self.truths.append(expr)
                self.truths += [i for i in inferences if i not in self.truths]

                truths_copy = self.truths.copy()
                self.infer_all()
                new_truths = [i for i in self.truths if i not in truths_copy and i not in inferences]
                if new_truths:
                    print(f"\t[info]This also entails[/]\t{new_truths}.")

            print(f"\t[info]Truths[/]\t{self.truths}.")


            for i in self.truths:
                if i not in truths_copy:
                    self.record[simplify(i)] = name

        else:
            print(f"[correct][bold]P{name}.[/] {expr}")
            print(f"\t[warning][bold]P{name}[/bold] is already known to be true.[/warning]\n")

        #print(f"[debug]{self.record=}[/]")
        print()

    def conclusion_stmt(self, args):
        name, expr = args
        name = int(name.value[1:-1])

        if expr in self.truths:
            print(f"[correct][bold]C{name}.[/] {expr}")
            print(f"\t[correct][bold]C{name}[/bold] is correct.[/correct]\n")
        elif LangNot(expr) in self.truths:
            print(f"[incorrect][bold]C{name}.[/] {expr}")
            if simplify(expr) in self.record:
                print(f"\t[incorrect][bold]C{name}[/bold] is a contradiction of [/]{simplify(LangNot(expr))} [incorrect]from [bold]{self.record[simplify(LangNot(expr))]}[/bold].[/incorrect]\n")
            else:
                print(f"\t[incorrect][bold]C{name}[/bold] is a contradiction of [/]{simplify(LangNot(expr))}[incorrect].[/incorrect]\n")
            self.is_correct = False
        else:
            print(f"[incorrect][bold]C{name}.[/] {expr}")
            print(f"\t[incorrect][bold]C{name}[/bold] has not been shown.[/incorrect]\n")
            self.is_correct = False

    def variable(self, args) -> LangVariable:
        return LangVariable(args[0])

    def l_and(self, args) -> LangExpression:
        return LangAnd(*args)
    
    def l_implies(self, args) -> LangExpression:
        return LangImplies(*args)

    def l_or(self, args) -> LangExpression:
        return LangOr(*args)

    def l_not(self, args) -> LangExpression:
        return LangNot(args[0])

with open("grammar.lark") as f:
    grammar = f.read()

transformer = LangTransformer()
parser = Lark(grammar, transformer=transformer, parser="lalr")