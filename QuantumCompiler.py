import re

class Lexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.tokens = []  
        self.token_specification = [
            ('QUANTUM_KEYWORD', r'qubit|H|CNOT|MEASURE|X|Y|Z|S|T|RX|RY|RZ|CX|CZ|SWAP|CCNOT|U3|U2|U1|bit'), 
            ('ARROW', r'->'),
            ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),  
            ('SEMICOLON', r';'), 
            ('COMMA', r','), 
            ('NUMBER', r'\d+(\.\d*)?'), 
            ('LPAREN', r'\('),  
            ('RPAREN', r'\)'),  
            ('SKIP', r'[ \t\n]+'),  
            ('MISMATCH', r'.'),  
        ]

    def tokenize(self):
        token_regex = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in self.token_specification)
        line_number = 1
        line_start = 0

        for match in re.finditer(token_regex, self.source_code):
            kind = match.lastgroup 
            lex = match.group() 
            column_start = match.start() - line_start + 1  
            column_end = match.end() - line_start  
            if kind == 'SKIP':
                if '\n' in lex:
                    line_number += lex.count('\n')  
                    line_start = match.end()  
                continue
            elif kind == 'MISMATCH':
                raise SyntaxError(f'Caractere inesperado {lex!r} na linha {line_number}, coluna {column_start}')
            else:
                token_length = len(lex)  
                self.tokens.append({
                    'Lexema': lex,
                    'Token': kind,
                    'Valor': token_length,
                    'Linha': line_number,
                    'Coluna_Inicial': column_start,
                    'Coluna_Final': column_end,
                })

        return self.tokens

    def print_tokens_table(self):
        output = f"{'Lexema':<20}{'Token':<20}{'Valor':<10}{'Linha':<10}{'Coluna Inicial':<15}{'Coluna Final':<15}\n"
        output += "-" * 90 + "\n"
        for token in self.tokens:
            output += f"{token['Lexema']:<20}{token['Token']:<20}{token['Valor']:<10}{token['Linha']:<10}{token['Coluna_Inicial']:<15}{token['Coluna_Final']:<15}\n"
        return output  

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.current_token = self.tokens[self.current_token_index] if self.tokens else None

    def advance(self):
        self.current_token_index += 1
        if self.current_token_index < len(self.tokens):
            self.current_token = self.tokens[self.current_token_index]
        else:
            self.current_token = None

    def consume(self, expected_type):
        if self.current_token and self.current_token['Token'] == expected_type:
            self.advance()
        else:
            raise SyntaxError(
                f"Esperado {expected_type}, mas encontrado {self.current_token['Token']} "
                f"no token '{self.current_token['Lexema']}' na linha {self.current_token['Linha']}."
            )

    def parse_program(self):
        statements = []
        while self.current_token is not None:
            statements.append(self.parse_statement())
        return statements

    def parse_statement(self):
        if self.current_token['Lexema'] == 'bit':
            statement = self.parse_bit_declaration()
        else:
            statement = self.parse_quantum_command()
        self.consume('SEMICOLON')
        return statement

    def parse_quantum_command(self):
        operation = self.current_token['Lexema']
        self.consume('QUANTUM_KEYWORD')
        arguments = self.parse_arguments()
        return {'operation': operation, 'arguments': arguments}

    def parse_bit_declaration(self):
        self.consume('QUANTUM_KEYWORD')
        bit_name = self.current_token['Lexema']
        self.consume('IDENTIFIER')
        return {'operation': 'DECLARE_BIT', 'arguments': [bit_name]}

    def parse_arguments(self):
        arguments = []
        arguments.append(self.current_token['Lexema'])
        self.consume('IDENTIFIER')
        while self.current_token and self.current_token['Token'] == 'COMMA':
            self.consume('COMMA')
            arguments.append(self.current_token['Lexema'])
            self.consume('IDENTIFIER')
        return arguments
    
class SemanticError(Exception):
    pass

class SemanticAnalyzer:
    def __init__(self, ast):
        self.ast = ast
        self.qubits = set()
        self.bits = set()

    def analyze(self):
        for statement in self.ast:
            self.check_statement(statement)

    def check_statement(self, statement):
        operation = statement['operation']
        arguments = statement['arguments']
        if operation == 'qubit':
            # declara o qubit somente se nao tiver sido declarado antes
            self.declare_qubit(arguments[0]) 
        elif operation == 'DECLARE_BIT':
            self.declare_bit(arguments[0])
        elif operation == 'MEASURE':
            self.check_measure(arguments)
        else:
            self.check_quantum_operation(operation, arguments)

    def check_measure(self, arguments):
        if len(arguments) != 2:
            raise SemanticError(f"Operação MEASURE requer 2 argumentos, mas recebeu {len(arguments)}.")
        qubit, bit = arguments
        if qubit not in self.qubits:
            raise SemanticError(f"Qubit '{qubit}' usado na medição não foi declarado.")
        if bit not in self.bits:
            raise SemanticError(f"Bit clássico '{bit}' usado na medição não foi declarado.")

    def check_quantum_operation(self, operation, arguments):
        if operation in {'H', 'X', 'Y', 'Z', 'S', 'T'}:
            if len(arguments) != 1:
                raise SemanticError(f"Operação {operation} requer exatamente 1 argumento, mas recebeu {len(arguments)}.")
            qubit = arguments[0]
            if qubit not in self.qubits:
                raise SemanticError(f"Qubit '{qubit}' usado na operação '{operation}' não foi declarado.")
        elif operation in {'CNOT', 'CX', 'CZ', 'SWAP'}:
            if len(arguments) != 2:
                raise SemanticError(f"Operação {operation} requer exatamente 2 argumentos, mas recebeu {len(arguments)}.")
            for qubit in arguments:
                if qubit not in self.qubits:
                    raise SemanticError(f"Qubit '{qubit}' usado na operação '{operation}' não foi declarado.")
        elif operation in {'U3', 'U2', 'U1', 'RX', 'RY', 'RZ'}:
            if len(arguments) < 1:
                raise SemanticError(f"Operação {operation} requer pelo menos 1 argumento (um qubit).")
            qubit = arguments[0]
            if qubit not in self.qubits:
                raise SemanticError(f"Qubit '{qubit}' usado na operação '{operation}' não foi declarado.")
        else:
            raise SemanticError(f"Operação desconhecida: '{operation}'.")

    def declare_qubit(self, qubit_name):
        if qubit_name in self.qubits:
            return  # n aofaz nada se o qubit ja estiver declarado
        self.qubits.add(qubit_name) 

    def declare_bit(self, bit):
        if bit in self.bits:
            return 
        self.bits.add(bit) 


if __name__ == "__main__":
    input_file = 'input.txt'
    output_file = 'output.txt'

    with open(input_file, 'r') as file:
        source_code = file.read()

    lexer = Lexer(source_code)
    try:
        tokens = lexer.tokenize()
        tokens_table = lexer.print_tokens_table()

        parser = Parser(tokens)
        ast = parser.parse_program()

        semantic_analyzer = SemanticAnalyzer(ast)
        semantic_analyzer.declare_qubit('q1')
        semantic_analyzer.declare_qubit('q2')
        semantic_analyzer.declare_bit('b1')
        semantic_analyzer.analyze()

        with open(output_file, 'w') as file:
            file.write("Tabela de Tokens:\n")
            file.write(tokens_table)
            file.write("\nÁrvore de Sintaxe Abstrata (AST):\n")
            file.write(str(ast))
            file.write("\nAnálise semântica concluída sem erros.\n")

        print(f"Análise salva em '{output_file}'.")
    except SyntaxError as e:
        print("Erro de Sintaxe:", e)
    except SemanticError as e:
        print("Erro Semântico:", e)