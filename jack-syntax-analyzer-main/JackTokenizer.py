from collections import deque
import xml.etree.ElementTree as ET
import os

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
    
def get_xml_file_path(jack_file_path, file_name, include_T = 1):
    file_name = os.path.join(os.path.split(jack_file_path)[-1], file_name[:-5]) + include_T*'T' + '.xml'
    return os.path.join('XML', file_name)

def get_jack_files(jack_file_path):
    jack_files = []
    for file_name in os.listdir(jack_file_path):
        if file_name[-5:] == '.jack':
            jack_files.append(file_name)
    return jack_files

def make_xml_directory(jack_file_path):
    os.makedirs(os.path.join('XML', os.path.split(jack_file_path)[-1]), exist_ok = True)

def main(jack_file_path):

    # Find all jack files, and make directory to store xml files
    jack_files = get_jack_files(jack_file_path)
    make_xml_directory(jack_file_path)

    # Generate a xml file for each jack file
    xml_files = []
    for file_name in jack_files:

        # Create tokenizer for this jack file
        file_path = os.path.join(jack_file_path, file_name)
        tokenizer = Tokenizer(file_path)

        # Iterate through file token by token adding child leaf nodes to the token tree all at the same depth of 1
        root = ET.Element('tokens')
        while tokenizer.has_more_tokens():
            tokenizer.advance()
            token_type = tokenizer.token_type()
            element = ET.SubElement(root, token_type)

            # Don't use quotation marks in XML file
            if token_type == 'string_constant':
                element.text = ' ' + tokenizer.current_token[1:-1] + ' '
            else:
                element.text = ' ' + tokenizer.current_token + ' '
        
        # Don't forget to close jack file
        tokenizer.jack_file.close()

        # Write tree to xml file
        xml_file_path = get_xml_file_path(jack_file_path, file_name)
        xml_files.append(xml_file_path)
        tree = ET.ElementTree(root)
        tree.write(xml_file_path)

    print(f'{" ".join(jack_files)} tokenized at {" ".join(xml_files)}')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Tokenize Jack file(s)")
    parser.add_argument('jack_file_path', type=str, help="The input Jack directory path")
    
    args = parser.parse_args()

    main(args.jack_file_path)