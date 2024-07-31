import os

class Parser:
    '''Encapsulates access to the input code. Reads an assembly language command, parses it, and provides convenient access to the command’s components
    (fields and symbols). In addition, removes all white space and comments
    '''

    def __init__(self, asm_file_path):
        '''Opens the input file/stream andgets ready to parse it.'''

        self.asm_file = open(asm_file_path, 'r')
        self.next_command = self.asm_file.readline()

    def has_more_commands(self):
        ''' Are there more commands in the input?'''

        if not self.next_command:
            return False
        
        # Deletes whitespace and comments
        while (self.next_command.strip() == '') or (self.next_command.strip()[0] == '/'):
            self.next_command = self.asm_file.readline()

            if not self.next_command:
                return False
        
        return True

    def advance(self):
        '''Reads the next command from the input and makes it the current command. 
        Should be called only if hasMoreCommands() is true. 
        Initially there is no current command.
        '''

        self.current_command = self.next_command.strip()
        self.next_command = self.asm_file.readline()

    def commandType(self):
        '''Returns the type of the current command:
            - A_COMMAND for @Xxx where Xxx is either a symbol or a decimal number
            - C_COMMAND for dest=comp;jump
            - L_COMMAND (actually, pseudocommand) for (Xxx) where Xxx is a symbol.
        '''

        first_char = self.current_command[0]

        if first_char == '@':
            return 'A_COMMAND'
        if first_char == '(':
            return 'L_COMMAND'
        return 'C_COMMAND'
    
    def symbol(self):
        '''Returns the symbol or decimal Xxx of the current command@Xxx or (Xxx). 
        Should be called only when commandType() is A_COMMAND or L_COMMAND.
        '''

        return self.current_command.split('@')[-1].strip('()')

    def dest(self):
        '''Returns the dest mnemonic in the current C-command (8 possibilities). 
        Should be called only when commandType() is C_COMMAND.
        '''

        if '=' not in self.current_command:
            return ''
        return self.current_command.split('=')[0]
    
    def comp(self):
        ''' Returns the comp mnemonic in the current C-command (28 possibilities). 
        Should be called only when commandType() is C_COMMAND.
        '''

        return self.current_command.split('=')[-1].split(';')[0]
    
    def jump(self):
        '''Returns the jump mnemonic in the current C-command (8 possibilities). 
        Should be called only when commandType() is C_COMMAND.
        '''

        if ';' not in self.current_command:
            return ''
        
        return self.current_command.split(';')[-1]

class Decoder:
    '''Translates Hack assembly language mnemonics into binary codes.'''

    def __init__(self):
        '''Tables for decoding'''

        self.d_table = {
            "": "000",
            "M": "001",
            "D": "010",
            "MD": "011",
            "A": "100",
            "AM": "101",
            "AD": "110",
            "AMD": "111"
        }

        self.c_table = {
            "0": "0101010",
            "1": "0111111",
            "-1": "0111010",
            "D": "0001100",
            "A": "0110000",
            "M": "1110000",
            "!D": "0001101",
            "!A": "0110001",
            "!M": "1110001",
            "-D": "0001111",
            "-A": "0110011",
            "-M": "1110011",
            "D+1": "0011111",
            "A+1": "0110111",
            "M+1": "1110111",
            "D-1": "0001110",
            "A-1": "0110010",
            "M-1": "1110010",
            "D+A": "0000010",
            "D+M": "1000010",
            "D-A": "0010011",
            "D-M": "1010011",
            "A-D": "0000111",
            "M-D": "1000111",
            "D&A": "0000000",
            "D&M": "1000000",
            "D|A": "0010101",
            "D|M": "1010101"
        }

        self.j_table = {
            "": "000",
            "JGT": "001",
            "JEQ": "010",
            "JGE": "011",
            "JLT": "100",
            "JNE": "101",
            "JLE": "110",
            "JMP": "111"
        }
    
    def dest(self, mnemonic):
        '''Returns the binary code of the dest mnemonic.'''

        return self.d_table[mnemonic]
    
    def comp(self, mnemonic):
        '''Returns the binary code of the comp mnemonic.'''

        return self.c_table[mnemonic]
    
    def jump(self, mnemonic):
        '''Returns the binary code of the jump mnemonic.'''
        
        return self.j_table[mnemonic]

class SymbolTable:
    '''Keeps a correspondence between symbolic labels and numeric addresses.'''

    def __init__(self):
        '''Initialize predefined symbols'''

        self.table = {
            "R0": 0,
            "R1": 1,
            "R2": 2,
            "R3": 3,
            "R4": 4,
            "R5": 5,
            "R6": 6,
            "R7": 7,
            "R8": 8,
            "R9": 9,
            "R10": 10,
            "R11": 11,
            "R12": 12,
            "R13": 13,
            "R14": 14,
            "R15": 15,
            "SCREEN": 16384,
            "KBD": 24576,
            "SP": 0,
            "LCL": 1,
            "ARG": 2,
            "THIS": 3,
            "THAT": 4
        }

    def add_entry(self, symbol, address):
        '''Adds the pair (symbol, address) to the table.'''

        self.table[symbol] = address

    def contains(self, symbol):
        '''Does the symbol table contain the given symbol?'''

        return symbol in self.table
    
    def get_address(self, symbol):
        '''Returns the address associated with the symbol.'''
        
        return self.table[symbol]

def get_hack_file_path(asm_file_path):
    filename = os.path.split(asm_file_path)[-1][:-4] + '.hack'
    return os.path.join('Hack', filename)

def main(asm_file_path):
    # Create parser for first pass. Create decoder and symbol table.
    symbol_parser = Parser(asm_file_path)
    decoder = Decoder()
    symbol_table = SymbolTable()
    
    # First pass, check for L commands and save their symbols address pairs to table, track command address by incrementing command number
    command_number = 0
    while symbol_parser.has_more_commands():
        # Go to next command
        symbol_parser.advance()

        # Check for L command
        if symbol_parser.commandType() == 'L_COMMAND':
            symbol_table.add_entry(symbol_parser.symbol(), command_number)
        else:
            # Increment command number if A or C command
            command_number+=1
    symbol_parser.asm_file.close()

    # Create parser for second pass
    parser = Parser(asm_file_path)
        
    # Open output hack file
    hack_file_path = get_hack_file_path(asm_file_path)
    with open(hack_file_path, 'w') as hack_file:

        # Go line by line through assembly file converting each command into its corresponding hack machine language code until no more commands
        # Second pass, replace existing symbols with corresponding addresses from table, new symbols are added to table starting from address 16
        var_address = 16
        while parser.has_more_commands():
            # Go to next command
            parser.advance()
            
            # Get command type
            command_type = parser.commandType()

            # Skip if L command
            if command_type == 'L_COMMAND': continue

            # In case of a C command find use parser to get each mnemonic and use decoder to get its bits and combine
            if command_type == 'C_COMMAND':
                code = '111'

                code += decoder.comp(parser.comp())
                code += decoder.dest(parser.dest())
                code += decoder.jump(parser.jump())
            # Otherwise if A command just convert the provided number or symbol into 15 bit binary form
            else:
                symbol = parser.symbol()
                
                # Check if symbol
                if not symbol.isdigit():
                    # Check if variable
                    if symbol_table.contains(symbol):
                        symbol = symbol_table.get_address(symbol)
                    else:
                        # Add new variable entry and increment the address for new ones
                        symbol_table.add_entry(symbol, var_address)
                        symbol = var_address

                        var_address+=1
                else:
                    symbol = int(symbol)
                
                code = '0' + format(symbol, '015b')
            
            # Write code to hack file
            hack_file.write(code + '\n')
    parser.asm_file.close()

    print(asm_file_path + ' translated to ' + hack_file_path)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Translate an assembly file into hack machine language")
    parser.add_argument('asm_file_path', type=str, help="The input assembly file")
    
    args = parser.parse_args()

    main(args.asm_file_path)

