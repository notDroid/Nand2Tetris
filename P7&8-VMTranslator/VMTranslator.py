import os

class Parser:
    '''Handles the parsing of a single .vm file, and encapsulates access to the input code. 
    It reads VM commands, parses them, and provides convenient access to their components. 
    In addition, it removes all white space and comments.
    '''

    def __init__(self, vm_file_path):
        '''Opens the input file/stream and gets ready to parse it.'''

        self.vm_file = open(vm_file_path, 'r')
        self.next_command = self.vm_file.readline()

        # Define the list of known arithmetic commands.
        self.arithmetic_commands = ["add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"]

        # Name conversion table for commands
        self.command_table = {
            'push': 'C_PUSH',
            'pop': 'C_POP',
            'label': 'C_LABEL',
            'goto': 'C_GOTO',
            'if-goto': 'C_IF',
            'function': 'C_FUNCTION',
            'return': 'C_RETURN',
            'call': 'C_CALL'
        }

    def has_more_commands(self):
        ''' Are there more commands in the input?'''

        if not self.next_command:
            return False
        
        # Skips whitespace and full comment lines
        while (self.next_command.strip() == '') or (self.next_command.strip()[0] == '/'):
            self.next_command = self.vm_file.readline()

            if not self.next_command:
                return False
        
        return True

    def advance(self):
        '''Reads the next command from the input and makes it the current command. 
        Should be called only if hasMoreCommands() is true. 
        Removes whitespace and comments.
        '''
        
        # Removes comments
        self.next_command = self.next_command.split("/")[0]

        # Current command is an array, its elements the command itself and arguments following
        self.current_command = self.next_command.strip().split(" ")
        self.next_command = self.vm_file.readline()

    def command_type(self):
        """Returns the type of the current command."""

        # Extract the current command from the input line.
        cmd = self.current_command[0]
        # Determine the type of the current command.
        if cmd in self.arithmetic_commands:
            return "C_ARITHMETIC"
        else:
            return self.command_table[cmd]
        
    def arg1(self):
        '''Returns the first command argument, or command itself in case of the command type C_ARITHMETIC'''

        if self.command_type() == 'C_ARITHMETIC':
            return self.current_command[0]
        return self.current_command[1]
    
    def arg2(self):
        '''Returns the second command argument'''

        return self.current_command[2]
    
class CodeWriter:
    '''Translates VM commands into Hack assembly code.'''

    def __init__(self):
        '''Initializes command conversion tables and labels'''

        # For write_arithmetic
        self.arithmetic_table = lambda: {
            'add': '@SP\nAM=M-1\nD=M\n@SP\nA=M-1\nM=D+M\n',
            'sub': '@SP\nAM=M-1\nD=M\n@SP\nA=M-1\nM=M-D\n',
            'and': '@SP\nAM=M-1\nD=M\n@SP\nA=M-1\nM=D&M\n',
            'or': '@SP\nAM=M-1\nD=M\n@SP\nA=M-1\nM=D|M\n',
            'eq': f'@SP\nAM=M-1\nD=M\n@SP\nA=M-1\nD=M-D\nM=-1\n@{self.jump_label}\nD;JEQ\n@SP\nA=M-1\nM=0\n({self.jump_label})\n',
            'gt': f'@SP\nAM=M-1\nD=M\n@SP\nA=M-1\nD=M-D\nM=-1\n@{self.jump_label}\nD;JGT\n@SP\nA=M-1\nM=0\n({self.jump_label})\n',
            'lt': f'@SP\nAM=M-1\nD=M\n@SP\nA=M-1\nD=M-D\nM=-1\n@{self.jump_label}\nD;JLT\n@SP\nA=M-1\nM=0\n({self.jump_label})\n',
            'not': '@SP\nA=M-1\nM=!M\n',
            'neg': '@SP\nA=M-1\nM=!M\nM=M+1\n'
        }

        ### For write_push_pop
        self.jump_label = 'jumplabel0'

        self.segment_table = {
            'local': 'LCL',
            'argument': 'ARG',
            'this': 'THIS',
            'that': 'THAT',
            'pointer': '3',
            'temp': '5',
            'static': '16'
        }

        self.push_pop_table = lambda segment, index: {
            'push': f'@{index}\nD=A\n@{segment}\nA=D+M\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n',
            'pop': f'@{index}\nD=A\n@{segment}\nD=D+M\n@R13\nM=D\n@SP\nAM=M-1\nD=M\n@R13\nA=M\nM=D\n'
        }
        self.get_pointer_temp_code = lambda segment, index: {
            'push': f'@{index}\nD=A\n@{segment}\nA=D+A\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n',
            'pop': f'@{index}\nD=A\n@{segment}\nD=D+A\n@R13\nM=D\n@SP\nAM=M-1\nD=M\n@R13\nA=M\nM=D\n'
        }
        self.get_static_code = lambda index: {
            'push': f'@{self.file_name}.{index}\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n',
            'pop': f'@SP\nAM=M-1\nD=M\n@{self.file_name}.{index}\nM=D\n'
        }
        self.get_constant_code = lambda index: f'@{index}\nD=A\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'
        ###

        # For write_if
        self.if_code = lambda label: f'@SP\nAM=M-1\nD=M\n@{self.function}${label}\nD;JNE\n'

        # For write_call
        self.return_address = 'return_address0'
        
        self.push_pop_pointer = lambda pointer: {
            'push': f'@{pointer}\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n',
            'pop': f'@{pointer}\nD=A\n@R13\nM=D\n@SP\nAM=M-1\nD=M\n@R13\nA=M\nM=D\n'
        } # Takes pointer like LCL and pushes its address onto stack, *not the value on the segment it points to

    def set_file_name(self, file_name):
        self.file_name = file_name

    def write_init(self):
        '''Initializes stack pointer to 256 then calls Sys.init'''

        init_code = '@256\nD=A\n@SP\nM=D\n' # SP = 256
        init_code += '@Sys.init\n0;JMP\n' # call Sys.init
        return init_code

    def write_arithmetic(self, command):
        '''Translates C_ARITHMETIC commands'''

        code = self.arithmetic_table()[command]

        # Increment jump label if used
        if command in ['eq', 'gt', 'lt']:
            jump_number = int(self.jump_label[-1]) + 1
            self.jump_label = self.jump_label[:-1] + str(jump_number)

        return code

    def write_push_pop(self, command, segment, index):
        '''Translates C_PUSH and C_POP commands'''

        if segment == 'constant':
            return self.get_constant_code(index)
        
        segment = self.segment_table[segment]

        # Pointer and Temp segments
        if segment in ['3', '5']:
            return self.get_pointer_temp_code(segment, index)[command]
        
        # Static segment
        if segment == '16':
            return self.get_static_code(index)[command]
        
        # LCL, ARG, THIS, THAT segments
        return self.push_pop_table(segment, index)[command]
    
    def write_label(self, label):
        '''Write function scoped labels that can be jumped to by goto commands (function$label)'''

        return f'({self.function}${label})\n'
    
    def write_goto(self, label):
        '''Unconditionally jump to specified label'''

        return f'@{self.function}${label}\n0;JMP\n'
    
    def write_if(self, label):
        '''Conditionally jump to specified label if latest stack element -1 (true) or don't if 0 (false)'''

        return self.if_code(label)
    
    def write_call(self, function_name, n_args):
        '''Create a new frame for the called function with hidden arguments when returning'''

        # push constant return_address
        code = self.write_push_pop('push', 'constant', self.return_address)

        # push LCL
        code += self.push_pop_pointer('LCL')['push']

        # push ARG
        code += self.push_pop_pointer('ARG')['push']

        # push THIS
        code += self.push_pop_pointer('THIS')['push']

        # push THAT
        code += self.push_pop_pointer('THAT')['push']

        # ARG = SP - n_arg - 5
        code += f'@SP\nD=M\n@{n_args}\nD=D-A\n@5\nD=D-A\n@ARG\nM=D\n'

        # LCL = SP
        code += '@SP\nD=M\n@LCL\nM=D\n'

        # goto function
        code += f'@{function_name}\n0;JMP\n'

        # Define return address label
        code += f'({self.return_address})\n'

        # Increment return address
        self.n_return_labels = int(self.return_address[-1]) + 1
        self.return_address = self.return_address[:-1] + str(self.n_return_labels)

        return code
    
    def write_return(self):
        '''Go back to previous function by setting function info to its caller (set SP, ARG, ...), append the return value to the top of the stack replacing the first argument, and goto return address'''

        # FRAME (R14) = LCL
        code = '@LCL\nD=M\n@R14\nM=D\n'

        # RET (R15) = *(FRAME - 5)
        code += '@5\nA=D-A\nD=M\n@R15\nM=D\n'

        # *ARG = pop()
        code += self.write_push_pop('pop', 'argument', 0)

        # SP = ARG + 1
        code += '@ARG\nD=M\n@1\nD=D+A\n@SP\nM=D\n'

        # Set caller's LCL, ARG, THIS, THAT
        for segment in ['LCL', 'ARG', 'THIS', 'THAT']:
            code += f'@R14\nAM=M-1\nD=M\n@{segment}\nM=D\n'
        
        # goto RET
        code += '@R15\nA=M\n0;JMP\n'

        return code

    def write_function(self, function_name, n_locals):
        '''Create function label and initialize local variables to 0'''

        # Set current function name (for local labels and gotos), and function label for calls
        self.function = function_name
        code = f'({function_name})\n'
        # push 0 n times
        for _ in range(n_locals):
            code += self.write_push_pop('push', 'constant', 0)
        return code 

def get_asm_file_path(vm_file_path):
    file_name = os.path.split(vm_file_path)[-1] + '.asm'
    return os.path.join('Assembly', file_name)

def get_vm_files(vm_file_path):
    vm_files = []
    for file in os.listdir(vm_file_path):
        if file[-3:] == '.vm':
            vm_files.append(file)
    return vm_files

def main(vm_file_path):
    # Create writer object that translates commands
    writer = CodeWriter()
    
    # Get vm files
    vm_files = get_vm_files(vm_file_path)

    # Open (and create) assembly file
    asm_file_path = get_asm_file_path(vm_file_path)
    with open(asm_file_path, 'w') as asm_file:
        # Write init (bootstrap) code
        asm_file.write(writer.write_init())

        # Iterate through .vm files
        for file in vm_files:
            # Create parser for file
            file_path = os.path.join(vm_file_path, file)
            parser = Parser(file_path)

            # Get and set file name for writer (for static pointer variables {file_name.index})
            writer.set_file_name(file[:-3])

            # Iterate through commands in file
            while parser.has_more_commands():
                # Go to next command and get its type
                parser.advance()
                command_type = parser.command_type()
                
                # Translate code based on what type it is
                if command_type == 'C_ARITHMETIC':
                    code = writer.write_arithmetic(parser.arg1())
                elif command_type in ['C_PUSH', 'C_POP']:
                    code = writer.write_push_pop(*parser.current_command)
                elif command_type == 'C_LABEL':
                    code = writer.write_label(parser.arg1())
                elif command_type == 'C_GOTO':
                    code = writer.write_goto(parser.arg1())
                elif command_type == 'C_IF':
                    code = writer.write_if(parser.arg1())
                elif command_type == 'C_FUNCTION':
                    code = writer.write_function(parser.arg1(), int(parser.arg2()))
                elif command_type == 'C_CALL':
                    code = writer.write_call(parser.arg1(), parser.arg2())
                elif command_type == 'C_RETURN':
                    code = writer.write_return()
                else:
                    raise NameError(f"No Command Type: {command_type}")
                
                # Write translated code to assembly file
                asm_file.write(code)
                #asm_file.write('// ' + ' '.join(parser.current_command) + '\n' + code) include comments

            # Don't forget to close vm file
            parser.vm_file.close()
    print(vm_file_path + ' translated to ' + asm_file_path)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Translate an VM file into assembly")
    parser.add_argument('vm_file_path', type=str, help="The input VM file")
    
    args = parser.parse_args()

    main(args.vm_file_path)
