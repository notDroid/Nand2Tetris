from collections import deque

class Tokenizer:
    '''Removes all comments and white space from the input stream 
    and breaks it into Jack-language tokens.
    '''
    
    def __init__(self, jack_file_path):
        '''Opens the input file/stream and gets ready to tokenize it.'''

        # Useful sets for O(1) in operations
        self.keywords = {
            'class', 'constructor', 'function', 
            'method', 'field', 'static', 'var', 
            'int', 'char', 'boolean', 'void', 'true', 
            'false', 'null', 'this', 'let', 'do', 
            'if', 'else', 'while', 'return'
        }

        self.symbols = {
            '{', '}', '(', ')', '[', ']', '.', 
            ',', ';' ,  '+' ,  '-', '*', '/', '&', 
            '|', '<', '>', '=', '~'
        }

        # Initialize tokenizing proccess by setting next tokens
        self.jack_file = open(jack_file_path, 'r')
        self.set_next_tokens()

    def has_more_tokens(self):
        '''Are there more tokens in the input?'''

        if (len(self.next_tokens) != 0):
            return True
        
        # If there are no more tokens in next tokens, go get the next tokens and hence see if there are more.
        return self.set_next_tokens()

    def set_next_line(self):
        '''Find next non comment/whitspace line and set it as next line, if there isn't a next line return False'''
        self.line = self.jack_file.readline()
        
        if not self.line:
            return False

        # Skips whitespace and full comment lines
        while (self.line.strip() == '') or (self.line.strip()[0] == '/') or (self.line.strip()[0] == '*'):
            self.line = self.jack_file.readline()

            if not self.line:
                return False
        
        # Removes comments after statements, then remove spaces before and after
        self.line = self.line.split("//")[0].strip() 
        return True

    def set_next_tokens(self):
        '''Go to next line (call self.set_next_line), then iterate through letters in line to find all tokens in it, returns False if no more tokens found'''
        
        # Get next line, and create token queue
        if not self.set_next_line():
            return False
        self.next_tokens = deque() # Supports popleft in O(1) (FIFO when using)
        
        # Use left right pointer  strategy, iterate through letters in line finding possible token segments or symbol tokens and updating left accordingly.
        left = 0
        quote = False

        # If space or symbol then add current segment--if not empty-- excluding the current letter, only add letter if its not a space (is a symbol)
        # This rule only breaks for strings in which case we keep skipping tokening until the second quote is reached and include the second quote as well.
        for right, letter in enumerate(self.line):
            
            if (letter == '\"'):
                quote = not quote
            if quote:
                continue

            segment = self.line[left:right + int(letter == '\"')]

            if (letter in self.symbols) or (letter == ' ') or (letter == '\"'):
                if segment != '':
                    self.next_tokens.append(segment)

                left = right + 1
                
            if (letter in self.symbols):
                self.next_tokens.append(self.line[right])

        return True
    
    def advance(self):
        '''Reads the next token from the input and makes it the current token. 
        Should be called only if has_more_tokens() is true. 
        '''

        self.current_token = self.next_tokens.popleft()

    def token_type(self):
        '''Returns the type of lexical element (token)'''

        if self.current_token in self.keywords:
            return 'keyword'
        if self.current_token in self.symbols:
            return 'symbol'
        if self.current_token.isdigit():
            return 'integer_constant'
        if (self.current_token[0] == "\""):
            return 'string_constant'
        if (not self.current_token[0].isdigit()):
            return 'identifier'
        
        raise SyntaxError(f"{self.current_token} violates a jack grammar rule")
