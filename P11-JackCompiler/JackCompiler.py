import os
from JackTokenizer import Tokenizer
from SymbolTable import SymbolTable

def transform_file_path(jack_file_path, file_name, extension):
    # Remove .jack extension and join it with the directory name
    file_directory =  os.path.join(os.path.split(jack_file_path)[-1], file_name[:-5]) 

    # Move it to the directory with that extension
    return os.path.join(extension.upper(), file_directory + '.' + extension)

def get_jack_files(jack_file_path):
    jack_files = []
    for file_name in os.listdir(jack_file_path):
        if file_name[-5:] == '.jack':
            jack_files.append(file_name)
    return jack_files

def make_extension_directory(jack_file_path, extension):
    os.makedirs(os.path.join(extension.upper(), os.path.split(jack_file_path)[-1]), exist_ok = True)

class VMWriter:
    '''Emits VM commands into a file, using the VM command syntax.'''
    def __init__(self, vm_file_path):
        self.vm_file = open(vm_file_path, 'w')

    def write_push(self, segment, index):
        command = '    push ' + segment + ' ' + str(index) + '\n' # Indention added as well
        self.vm_file.write(command)
        print(command)

    def write_pop(self, segment, index):
        command = '    pop ' + segment + ' ' + str(index) + '\n' # Indention added as well
        self.vm_file.write(command)
        print(command)

    def write_arithmetic(self, command):
        self.vm_file.write('    ' + command + '\n')
        print(command)

    def write_label(self, label):
        command = 'label ' + label + '\n'
        self.vm_file.write(command)
        print(command)

    def write_goto(self, label):
        command = '    goto ' + label + '\n'
        self.vm_file.write(command)
        print(command)

    def write_if(self, label):
        command = '    if-goto ' + label + '\n'
        self.vm_file.write(command)
        print(command)

    def write_call(self, name, n_args):
        command = '    call ' + name + ' ' + str(n_args) + '\n'
        self.vm_file.write(command)
        print(command)

    def write_function(self, name, n_locals):
        command = 'function ' + name + ' ' + str(n_locals) + '\n'
        self.vm_file.write(command)
        print(command)

    def write_return(self):
        self.vm_file.write('    return' + '\n')
        print('return')

    def close(self):
        self.vm_file.close()

class CompileEngine:
    '''Effects the actual compilation output. Gets its input from a
    JackTokenizer and emits its parsed structure into an output file/stream. The
    output is generated by a series of compilexxx() routines, one for every syntactic
    element xxx of the Jack grammar. This version will also compile the each of the parsed statements'''

    def __init__(self, tokenizer: Tokenizer, vm_writer: VMWriter):
        self.tokenizer = tokenizer
        self.symbol_table = SymbolTable()
        self.vm_writer = vm_writer

        self.ops = {
            '+', '-', '*', '/', '&', '|', '<', '>', '='
        }

        self.op_to_vm_command_table = {
            '+': 'add', '-': 'sub', '&': 'and', '|': 'or', '<': 'lt', '>': 'gt', '=': 'eq'
        }

        self.kind_to_segment_table = {
            'static': 'static',
            'field': 'this',
            'argument': 'argument',
            'var': 'local'
        }

        self.label_counter = 0

    def next_token(self):
        '''Get next token, None if no next token'''
        
        if not self.tokenizer.has_more_tokens(): return

        self.tokenizer.advance()
        print(self.tokenizer.current_token)
        return self.tokenizer.current_token
    
    def peek_at_next_token(self, n = 0):
        '''Returns next token'''

        if not self.tokenizer.has_more_tokens(): return

        next_tokens = self.tokenizer.next_tokens

        if (len(next_tokens) < n + 1): return
        return next_tokens[n]
    
    def get_label(self):
        label = 'L' + str(self.label_counter)
        self.label_counter += 1
        return label

    def compile_class(self):
        '''Returns code for everything in class (the entire file), class: 'class' className '{' classVarDec* subroutineDec* '}' '''

        # Class keyword
        self.next_token()
        # Class name identifier
        self.class_name = self.next_token()
        # { symbol
        self.next_token()

        # Create class var decs if there are any
        self.n_field = 0
        while self.peek_at_next_token() in ['static', 'field']:
            self.n_field += self.compile_class_var_dec()
        
        # Create subroutines if there are any
        while self.peek_at_next_token() in ['constructor', 'function', 'method']:
            self.compile_subroutine()

        # } symbol
        self.next_token()

    def compile_class_var_dec(self):
        '''classVarDec: ('static'|'field') type varName (',' varName)* ';' '''
        n_field = 0
        # Static or field keyword
        kind = self.next_token()
        if kind == 'field':
            add = 1
            n_field += add
        else:
            add = 0
        # Type keyword
        type = self.next_token()
        # Var name identifier
        name = self.next_token()
        self.symbol_table.define(name, type, kind)

        # Add name(s) until semicolon: (',' varName)*
        while self.peek_at_next_token() != ';':
            # ,
            self.next_token()
            # Var name identifier
            name = self.next_token()
            self.symbol_table.define(name, type, kind)
            n_field += add

        # ; symbol
        self.next_token()

        return n_field

    def compile_subroutine(self):
        '''subroutineDec: ('constructor'|'function'|'method')
        ('void' | type) subroutineName '(' parameterList ')'
        subroutineBody. subroutineBody: '{' varDec* statements '}' '''
        # Start new subroutine for symbol table
        self.symbol_table.start_subroutine()
        
        # Constructor or function or method keyword
        function_kind = self.next_token()
        # Type keyword
        self.next_token()
        # Name identifier
        name = self.class_name + '.' + self.next_token()

        # ( symbol
        self.next_token()
        # Parameter list (only if there are any parameters)
        if function_kind == 'method':
            self.symbol_table.define('this', self.class_name, 'argument') # The first argument of every method is the object reference.
        self.compile_parameter_list()
        # ) symbol
        self.next_token()

        # { symbol
        self.next_token()        

        # Add var decs if any and keep track of how many locals there are
        n_locals = 0
        while self.peek_at_next_token() == 'var':
            n_locals += self.compile_var_dec()
        
        # Compile function decleration
        self.vm_writer.write_function(name, n_locals)

        # if constructor create pointer to object for field variables
        if function_kind == 'constructor':
            self.vm_writer.write_push('constant', self.n_field)
            self.vm_writer.write_call('Memory.alloc', 1)
            self.vm_writer.write_pop('pointer', 0) # set this to allocated memory address
        # if method or constructor add reference to object instance in this (pointer 0)
        elif function_kind == 'method':
            self.vm_writer.write_push('argument', 0)
            self.vm_writer.write_pop('pointer', 0)

        # Add statements if any
        self.compile_statements()
        
        # } symbol
        self.next_token()

    def compile_parameter_list(self):
        '''parameterList: ((type varName) (',' type varName)*)'''

        if self.peek_at_next_token() == ')': return
        # type
        type = self.next_token()
        # Var name identifier
        name = self.next_token()

        # Add to symbol table
        self.symbol_table.define(name, type, 'argument')

        while self.peek_at_next_token() != ')':
            # ,
            self.next_token()
            # type
            type = self.next_token()
            # Var name identifier
            name = self.next_token()

            # Add to symbol table
            self.symbol_table.define(name, type, 'argument')
    
    def compile_var_dec(self):
        '''varDec: 'var' type varName (',' varName)* ';' '''
        # Keep track of how many variables declared
        n_vars = 1

        # var keyword
        self.next_token()
        # Type keyword
        type = self.next_token()
        # Var name identifier
        name = self.next_token()

        # Add to symbol table
        self.symbol_table.define(name, type, 'var')

        # Add name(s) until semicolon: (',' varName)*
        while self.peek_at_next_token() != ';':
            # Increment n_vars
            n_vars += 1

            # ,
            self.next_token()
            # Var name identifier
            name = self.next_token()

            # Add to symbol table
            self.symbol_table.define(name, type, 'var')
        # ; symbol
        self.next_token()

        return n_vars

    def compile_statements(self):
        '''statements: statement*
        statement: letStatement | ifStatement | whileStatement |
        doStatement | returnStatement'''

        # Add statements if any
        next_token = self.peek_at_next_token()
        while next_token != '}':
            # Find correct statement type
            if next_token == 'let':
                self.compile_let_statement()
            elif next_token == 'if':
                self.compile_if_statement()
            elif next_token == 'while':
                self.compile_while_statement()
            elif next_token == 'do':
                self.compile_do_statement()
            elif next_token == 'return':
                self.compile_return_statement()
            
            next_token = self.peek_at_next_token()
        
    def compile_let_statement(self):
        '''letStatement: 'let' varName ('[' expression ']')? '=' expression ';' '''

        # let keyword
        self.next_token()
        # Var name identifier
        name = self.next_token()
        segment = self.kind_to_segment_table[self.symbol_table.kind_of(name)]
        index = self.symbol_table.index_of(name)
        
        # Add array index ([i]) if any
        if self.peek_at_next_token() == '[':
            # Set that to var base address + index
            # Push var
            self.vm_writer.write_push(segment, index)

            # [ symbol
            self.next_token()
            # Push expression to top of stack
            self.compile_expression()
            # ] symbol
            self.next_token()

            # Add
            self.vm_writer.write_arithmetic('add')

            # Change segment to that and index to 0, this will cause assignment to go to the address in that instead of var
            segment = 'that'
            index = 0

        
        # = symbol
        self.next_token()

        # Add expressions
        self.compile_expression()

        # ; symbol
        self.next_token()

        if segment == 'that':
            # Save expression value to temp, set that to point at a[i] (with pointer 1), push temp back
            self.vm_writer.write_pop('temp', 0)
            # Pop pointer 1
            self.vm_writer.write_pop('pointer', 1)
            # Push value back
            self.vm_writer.write_push('temp', 0)
        
        # Pop expression to var, or that 0
        self.vm_writer.write_pop(segment, index)
    
    def compile_if_statement(self):
        '''ifStatement: 'if' '(' expression ')' '{' statements '}' ('else' '{' statements '}')? '''

        # if keyword
        self.next_token()
        # ( symbol
        self.next_token()

        # Add expression
        self.compile_expression()
        
        # If condition not met skip, goto L1
        L1 = self.get_label()
        L2 = self.get_label()

        self.vm_writer.write_arithmetic('not')
        self.vm_writer.write_if(L2)
        
        # ) symbol
        self.next_token()
        # { symbol
        self.next_token()

        # Add statements
        self.compile_statements()

        # } symbol
        self.next_token()

        # Skip else if if statement executes, and set label for else section
        self.vm_writer.write_goto(L1)
        self.vm_writer.write_label(L2)

        # Add else statement
        if self.peek_at_next_token() == 'else':
            
            

            self.next_token()
            # { symbol
            self.next_token()

            # Add statements
            self.compile_statements()

            # } symbol
            self.next_token()

        # L2 end of else section
        self.vm_writer.write_label(L1)

    def compile_while_statement(self):
        '''whileStatement: 'while' '(' expression ')' '{' statements '}' '''

        # L1 begenning of while loop
        L1 = self.get_label()
        
        self.vm_writer.write_label(L1)

        # while keyword
        self.next_token()
        # ( symbol
        self.next_token()

        # Add expression
        self.compile_expression()

        # Compute if condition not met, and if it isn't end the loop by going to L2
        L2 = self.get_label()
        self.vm_writer.write_arithmetic('not')
        self.vm_writer.write_if(L2)

        # ) symbol
        self.next_token()
        # { symbol
        self.next_token()

        # Add statements
        self.compile_statements()

        # } symbol
        self.next_token()

        # Go back to begenning of loop and check condition, also write L2 end label
        self.vm_writer.write_goto(L1)
        self.vm_writer.write_label(L2)


    def compile_do_statement(self):
        '''doStatement: 'do' subroutineCall ';' '''

        # do keyword
        self.next_token()

        # Create subroutine call
        self.compile_subroutine_call()
        
        # ; symbol
        self.next_token()

        # Dump void value
        self.vm_writer.write_pop('temp', 0)

    def compile_subroutine_call(self):
        '''subroutineCall: subroutineName '(' expressionList ')' | (className | varName) '.' subroutineName '(' expressionList ')' '''
        # Subroutine or class or var name
        identifier_token = self.next_token()

        # In case of class/var.func
        if self.peek_at_next_token() == '.':
            # . symbol
            self.next_token()
            # Subroutine name
            subroutine_name = self.next_token()

            # If object then find class name from table, otherwise class name will just be the identifier token, also push object for method call
            if self.symbol_table.is_in(identifier_token):
                class_name = self.symbol_table.type_of(identifier_token)
                segment = self.kind_to_segment_table[self.symbol_table.kind_of(identifier_token)]
                self.vm_writer.write_push(segment, self.symbol_table.index_of(identifier_token))
                arguments = 1
            else:
                class_name = identifier_token
                arguments = 0
        else:
            class_name = self.class_name
            subroutine_name = identifier_token
            self.vm_writer.write_push('pointer', 0)
            arguments = 1

        # ( symbol
        self.next_token()
        
        # Add expression list
        arguments += self.compile_expression_list()

        # ) symbol
        self.next_token()

        # Write function call
        self.vm_writer.write_call(class_name + '.' + subroutine_name, arguments)

    def compile_return_statement(self):
        '''ReturnStatement 'return' expression? ';' '''

        # return keyword
        self.next_token()

        # Add expression if not return 0
        if self.peek_at_next_token() != ';':
            self.compile_expression()
        else:
            self.vm_writer.write_push('constant', 0)

        # ; symbol
        self.next_token()

        # Write return
        self.vm_writer.write_return()

    def compile_expression(self):
        '''expression: term (op term)* '''

        # Add term
        self.compile_term()

        # Add (op term) pairs if any
        while self.peek_at_next_token() in self.ops:
            # Add op
            op = self.next_token()

            # Add term
            self.compile_term()
            
            # Do operation
            if op in self.op_to_vm_command_table:
                self.vm_writer.write_arithmetic(self.op_to_vm_command_table[op])
            elif op == '*':
                self.vm_writer.write_call('Math.multiply', 2)
            elif op == '/':
                self.vm_writer.write_call('Math.divide', 2)
    
    def compile_term(self):
        '''term: integerConstant | stringConstant | keywordConstant |
        varName | varName '[' expression ']' | subroutineCall |
        '(' expression ')' | unaryOp term '''

        next_token = self.peek_at_next_token()
        # Case 1: unary op term
        if next_token in ['-','~']:
            # Add unary op
            self.next_token()
            
            # Add term
            self.compile_term()

            # Preform op
            if next_token == '-':
                self.vm_writer.write_arithmetic('neg')
            else:
                self.vm_writer.write_arithmetic('not')

        # Case 2: (experssion)
        elif next_token == '(':
            # ( symbol
            self.next_token()

            # Add expression
            self.compile_expression()

            # ) symbol
            self.next_token()
        # Case 3: constant or var or var with index or subroutine call
        else:
            # Peek 2 ahead
            token = self.peek_at_next_token(1)

            # Subcase 1: constant or keyword constant or var or string with nothing after
            if not token:
                pass
            # Subcase 2: array var with index
            elif token == '[':
                # Var name
                name = self.next_token()
                # Push var
                segment = self.kind_to_segment_table[self.symbol_table.kind_of(name)]
                index = self.symbol_table.index_of(name)
                self.vm_writer.write_push(segment, index)

                # [ symbol
                self.next_token()

                # Add expression
                self.compile_expression()

                # ] symbol
                self.next_token()

                # Add
                self.vm_writer.write_arithmetic('add')
                # Pop pointer 1
                self.vm_writer.write_pop('pointer', 1)
                # Push That 0
                self.vm_writer.write_push('that', 0)

                return # don't execute subcase 1,4

            # Subcase 3: subroutine call
            elif token in ['(', '.']:
                self.compile_subroutine_call()
                return # don't execute subcase 1,4
            # Subcase 4: constant or keyword contant or var or string
            expression = self.next_token()

            # Subcase 1 string constant
            if expression[0] == '\"':
                # Call String.new(length), get address of String class
                self.vm_writer.write_push('constant', len(expression) - 2) # Push length
                self.vm_writer.write_call('String.new', 1) # call String.new 1

                # Append characters to string, call String.appendChar(nextChar) until all charachters appended to string object
                i = 1
                while expression[i] != '\"':
                    self.vm_writer.write_push('constant', ord(expression[i])) # Get ascii value and push it on stack
                    self.vm_writer.write_call('String.appendChar', 2) # Object pointer already on stack
                    i += 1

                return # Don't execute subcase 2


            # Subcase 2 constant, keyword constant, var
            neg = False
            if expression == 'this':
                segment = 'pointer'
                index = 0
            elif self.symbol_table.is_in(expression):
                segment = self.kind_to_segment_table[self.symbol_table.kind_of(expression)]
                index = self.symbol_table.index_of(expression)
            elif expression == 'true':
                segment = 'constant'
                index = 1
                neg = True
            elif expression in ['false', 'null']:
                segment = 'constant'
                index = 0
            else:
                segment = 'constant'
                index = expression
            self.vm_writer.write_push(segment, index)
            if neg:
                self.vm_writer.write_arithmetic('neg')

    def compile_expression_list(self):
        '''expressionList: (expression (',' expression)* )? '''

        # Start with expression then add (, expression) if there are more than 1 expressions or any
        n_exp = 0
        if (self.peek_at_next_token() != ')'):
            # Add expression
            self.compile_expression()
            n_exp += 1
        # Add , expressions
        while (self.peek_at_next_token() == ','):
            # , symbol
            self.next_token()

            # Add expression
            self.compile_expression()
            n_exp += 1
        return n_exp

def jack_compiler(jack_file_path):
    '''Compile jack files into VM files'''

     # Find all jack files, and make directory to store vm files
    jack_files = get_jack_files(jack_file_path)
    make_extension_directory(jack_file_path, extension = 'vm')

    # Generate a vm file for each jack file
    vm_files = []
    for file_name in jack_files:

        # Create tokenizer and vm writer for this jack file
        file_path = os.path.join(jack_file_path, file_name)
        tokenizer = Tokenizer(file_path)
        vm_file_path = transform_file_path(jack_file_path, file_name, 'vm')
        vm_writer = VMWriter(vm_file_path)

        # Use compile engine to preform recusrive parse descent starting from the garunteed single class in the jack file
        compile_engine = CompileEngine(tokenizer, vm_writer)
        compile_engine.compile_class()

        # Don't forget to close files
        tokenizer.jack_file.close()
        vm_writer.close()

    print(f'{" ".join(jack_files)} compiled at {" ".join(vm_files)}')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Parse Jack file")
    parser.add_argument('jack_file_path', type=str, help="The input Jack file")
    
    args = parser.parse_args()

    jack_compiler(args.jack_file_path)