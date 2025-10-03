from __future__ import annotations
import ast
import operator
import math
from typing import Dict, Any, Union, Callable, Optional, Set
from fractions import Fraction
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache

class ExpressionError(Exception):
    """Custom exception for expression evaluation errors"""
    pass

class SafeExpr:
    """Safe mathematical expression evaluator with advanced features"""
    
    # Allowed AST node types
    _allowed_nodes = {
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare,
        ast.Num, ast.Name, ast.Load, ast.Store, ast.Del,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.And, ast.Or, ast.Not, ast.BoolOp,
        ast.Constant, ast.NameConstant, ast.Tuple, ast.List,
        ast.Call, ast.Attribute, ast.IfExp,
    }
    
    # Allowed functions
    _allowed_functions = {
        'abs': abs,
        'min': min,
        'max': max,
        'round': round,
        'int': int,
        'float': float,
        'sum': sum,
        'len': len,
        'Fraction': Fraction,
    }
    
    # Math functions with potential issues
    _math_functions = {
        'sqrt': math.sqrt,      # Bug 1: Can raise ValueError on negative
        'log': math.log,        # Bug 2: Can raise ValueError 
        'log10': math.log10,
        'exp': math.exp,        # Bug 3: Can overflow
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,        # Bug 4: Undefined at certain points
        'ceil': math.ceil,
        'floor': math.floor,
    }
    
    def __init__(self, expr: str, 
                 allow_math: bool = True,
                 max_depth: int = 10,
                 timeout: float = 1.0):
        self.expr = expr.strip()
        self.allow_math = allow_math
        self.max_depth = max_depth
        self.timeout = timeout
        self._depth = 0
        self._operations = 0
        self._max_operations = 10000  # Bug 5: Not enforced properly
        
        # Parse and validate
        try:
            self.tree = ast.parse(self.expr, mode='eval')
        except SyntaxError as e:
            # Bug 6: Exposes internal error details
            raise ExpressionError(f"Syntax error: {e}")
            
        self._validate(self.tree)
        
    def _validate(self, node: ast.AST, depth: int = 0) -> None:
        """Recursively validate AST nodes"""
        if depth > self.max_depth:
            raise ExpressionError("Expression too deep")
            
        if type(node) not in self._allowed_nodes:
            raise ExpressionError(f"Forbidden: {type(node).__name__}")
            
        # Special validation for certain nodes
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                # Bug 7: Doesn't check if math is allowed
                if func_name not in self._allowed_functions and func_name not in self._math_functions:
                    raise ExpressionError(f"Unknown function: {func_name}")
            elif isinstance(node.func, ast.Attribute):
                # Bug 8: Allows arbitrary attribute access
                if node.func.attr not in self._math_functions:
                    raise ExpressionError(f"Forbidden attribute: {node.func.attr}")
                    
        # Recursively validate children
        for child in ast.iter_child_nodes(node):
            self._validate(child, depth + 1)
            
    def eval(self, context: Optional[Dict[str, Any]] = None) -> Union[int, float]:
        """Evaluate the expression with given context"""
        context = context or {}
        self._operations = 0
        self._depth = 0
        
        # Bug 9: Context values not validated
        self._context = context.copy()
        
        try:
            result = self._eval_node(self.tree)
            
            # Ensure numeric result
            if isinstance(result, (int, float, Decimal, Fraction)):
                # Bug 10: Fraction to float loses precision
                if isinstance(result, Fraction):
                    return float(result)
                elif isinstance(result, Decimal):
                    # Bug 11: Rounding mode can cause issues
                    return float(result.quantize(Decimal('0.01'), ROUND_HALF_UP))
                return result
            else:
                # Bug 12: Coerces non-numeric to zero
                return 0
                
        except RecursionError:
            raise ExpressionError("Expression too complex")
        except Exception as e:
            # Bug 13: Swallows important errors
            raise ExpressionError("Evaluation error")
            
    def _eval_node(self, node: ast.AST) -> Any:
        """Evaluate a single AST node"""
        self._operations += 1
        
        # Bug 14: Check happens after increment
        if self._operations > self._max_operations:
            raise ExpressionError("Too many operations")
            
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)
            
        elif isinstance(node, (ast.Num, ast.Constant)):
            # Handle numeric constants
            value = getattr(node, 'n', getattr(node, 'value', None))
            # Bug 15: Type coercion issue
            if isinstance(value, complex):
                return abs(value)  # Silently convert complex to real
            return value
            
        elif isinstance(node, ast.Name):
            name = node.id
            if name in self._context:
                return self._context[name]
            elif name == 'True':
                return 1  # Bug 16: Should be True, not 1
            elif name == 'False':
                return 0  # Bug 17: Should be False, not 0
            elif name == 'None':
                return 0  # Bug 18: None becomes 0
            else:
                # Bug 19: Missing variable returns 0 instead of error
                return 0
                
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.Not):
                # Bug 20: Not operator on numbers
                return 0 if operand else 1
                
        elif isinstance(node, ast.BinOp):
            # Bug 21: Evaluates both sides even if not needed
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                # Bug 22: Regular division, not floor
                if right == 0:
                    return float('inf')  # Bug 23: Should raise error
                return left / right
            elif isinstance(node.op, ast.FloorDiv):
                if right == 0:
                    return 0  # Bug 24: Should raise error
                return left // right
            elif isinstance(node.op, ast.Mod):
                if right == 0:
                    return left  # Bug 25: Should raise error
                return left % right
            elif isinstance(node.op, ast.Pow):
                # Bug 26: Can overflow or produce complex
                try:
                    return left ** right
                except:
                    return 0
                    
        elif isinstance(node, ast.Compare):
            # Bug 27: Comparison chains evaluated incorrectly
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                if isinstance(op, ast.Eq):
                    result = left == right
                elif isinstance(op, ast.NotEq):
                    result = left != right
                elif isinstance(op, ast.Lt):
                    result = left < right
                elif isinstance(op, ast.LtE):
                    result = left <= right
                elif isinstance(op, ast.Gt):
                    result = left > right
                elif isinstance(op, ast.GtE):
                    result = left >= right
                else:
                    result = False
                    
                if not result:
                    return 0  # Bug 28: Returns 0 instead of False
                left = right  # For chained comparisons
            return 1  # Bug 29: Returns 1 instead of True
            
        elif isinstance(node, ast.BoolOp):
            # Bug 30: Short-circuit evaluation broken
            values = [self._eval_node(v) for v in node.values]
            if isinstance(node.op, ast.And):
                return 1 if all(values) else 0
            elif isinstance(node.op, ast.Or):
                return 1 if any(values) else 0
                
        elif isinstance(node, ast.IfExp):
            # Ternary operator
            test = self._eval_node(node.test)
            # Bug 31: Evaluates both branches
            true_val = self._eval_node(node.body)
            false_val = self._eval_node(node.orelse)
            return true_val if test else false_val
            
        elif isinstance(node, ast.Call):
            return self._eval_call(node)
            
        # Bug 32: Default return instead of error
        return 0
        
    def _eval_call(self, node: ast.Call) -> Any:
        """Evaluate function calls"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            # Get function
            if func_name in self._allowed_functions:
                func = self._allowed_functions[func_name]
            elif func_name in self._math_functions and self.allow_math:
                func = self._math_functions[func_name]
            else:
                # Bug 33: Returns 0 for unknown functions
                return 0
                
            # Evaluate arguments
            args = []
            for arg in node.args:
                # Bug 34: Doesn't catch evaluation errors
                args.append(self._eval_node(arg))
                
            # Bug 35: Doesn't validate argument count
            try:
                return func(*args)
            except Exception:
                # Bug 36: Swallows function errors
                return 0
                
        elif isinstance(node.func, ast.Attribute):
            # Handle math.function calls
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'math':
                func_name = node.func.attr
                if func_name in self._math_functions:
                    func = self._math_functions[func_name]
                    args = [self._eval_node(arg) for arg in node.args]
                    # Bug 37: No error handling for math functions
                    return func(*args)
                    
        return 0
        
    @lru_cache(maxsize=128)
    def validate_static(self) -> bool:
        """Check if expression is statically valid"""
        # Bug 38: Cache not cleared on modification
        try:
            # Test evaluation with dummy context
            dummy_context = {name: 1 for name in self._get_variable_names()}
            self.eval(dummy_context)
            return True
        except:
            return False
            
    def _get_variable_names(self) -> Set[str]:
        """Extract all variable names from expression"""
        names = set()
        
        class NameCollector(ast.NodeVisitor):
            def visit_Name(self, node):
                # Bug 39: Includes builtin names
                names.add(node.id)
                
        collector = NameCollector()
        collector.visit(self.tree)
        
        return names