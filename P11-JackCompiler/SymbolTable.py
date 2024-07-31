class SymbolTable:
    '''Provides a symbol table abstraction. The symbol table associates the
    identifier names found in the program with identifier properties needed for compilation: type, kind, and running index. The symbol table for Jack programs has
    two nested scopes (class/subroutine).'''

    def __init__(self):
        self.class_table = dict()
        self.class_count_table = {'static': 0, 'field': 0}

        self.kind_of = lambda name: self.find_element(name, 'kind')
        self.type_of = lambda name: self.find_element(name, 'type')
        self.index_of = lambda name: self.find_element(name, 'index')
        
    def start_subroutine(self):
        self.subroutine_table = dict()
        self.subroutine_count_table = {'argument': 0, 'var': 0}

    def define(self, name, type, kind):
        if kind in ['static', 'field']:
            self.class_table[name] = {'type': type, 'kind': kind, 'index': self.class_count_table[kind]}
            self.class_count_table[kind] = self.class_count_table[kind] + 1
        else:
            self.subroutine_table[name] = {'type': type, 'kind': kind, 'index': self.subroutine_count_table[kind]}
            self.subroutine_count_table[kind] = self.subroutine_count_table[kind] + 1

    def find_element(self, name, element):
        if name in self.subroutine_table:
            return self.subroutine_table[name][element]
        return self.class_table[name][element]
    
    def is_in(self, name):
        if name in self.subroutine_table:
            return True
        if name in self.class_table:
            return True
        return False