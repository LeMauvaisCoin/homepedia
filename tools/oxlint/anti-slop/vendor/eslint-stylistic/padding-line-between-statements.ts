// Vendored from ESLint Stylistic; see UPSTREAM.md and LICENSE in this directory.
import type { ESTree, Context as RuleContext, SourceCode, Token as SyntaxToken, Comment, CreateRule, Location } from '@oxlint/plugins'
type ASTNode = ESTree.Node
type Token = SyntaxToken | Comment
import type {
  RuleOptions,
  SelectorOption,
  StatementOption,
} from './padding-line-options.d.ts'
import {
  isClosingBraceToken,
  isFunction,
  isNotSemicolonToken,
  isSemicolonToken,
  isSingleLine,
  isTokenOnSameLine,
  skipChainExpression,
} from './padding-line-ast.ts'

type NodeTest = (node: ASTNode, sourceCode: SourceCode) => boolean

interface NodeTestObject {
  test: NodeTest
}

function isSelectorOption(option: StatementOption): option is SelectorOption {
  return typeof option === 'object' && !Array.isArray(option)
}

/**
 * Creates tester which check if a node starts with specific keyword with the
 * appropriate AST_NODE_TYPES.
 * @param keyword The keyword to test.
 * @returns the created tester.
 * @private
 */
function newKeywordTester(
  type: string | string[],
  keyword: string,
): NodeTestObject {
  return {
    test(node, sourceCode): boolean {
      const isSameKeyword = sourceCode.getFirstToken(node)?.value === keyword
      const isSameType = Array.isArray(type)
        ? type.includes(node.type)
        : type === node.type

      return isSameKeyword && isSameType
    },
  }
}

/**
 * Creates tester which check if a node is specific type.
 * @param type The node type to test.
 * @returns the created tester.
 * @private
 */
function newNodeTypeTester(type: string): NodeTestObject {
  return {
    test: (node): boolean => node.type === type,
  }
}

/**
 * Checks the given node is an expression statement of IIFE.
 * @param node The node to check.
 * @returns `true` if the node is an expression statement of IIFE.
 * @private
 */
function isIIFEStatement(node: ASTNode): boolean {
  if (node.type === 'ExpressionStatement') {
    let expression = skipChainExpression(node.expression)
    if (expression.type === 'UnaryExpression')
      expression = skipChainExpression(expression.argument)

    if (expression.type === 'CallExpression') {
      let node: ASTNode = expression.callee
      while (node.type === 'SequenceExpression') {
        const lastExpression = node.expressions.at(-1)
        if (lastExpression === undefined)
          throw new Error('Padding rule invariant: sequence expression is empty')
        node = lastExpression
      }

      return isFunction(node)
    }
  }
  return false
}

/**
 * Checks whether the given node is a block-like statement.
 * This checks the last token of the node is the closing brace of a block.
 * @param sourceCode The source code to get tokens.
 * @param node The node to check.
 * @returns `true` if the node is a block-like statement.
 * @private
 */
function isBlockLikeStatement(
  node: ASTNode,
  sourceCode: SourceCode,
): boolean {
  // do-while with a block is a block-like statement.
  if (
    node.type === 'DoWhileStatement'
    && node.body.type === 'BlockStatement'
  ) {
    return true
  }

  /**
   * IIFE is a block-like statement specially from
   * JSCS#disallowPaddingNewLinesAfterBlocks.
   */
  if (isIIFEStatement(node))
    return true

  // Checks the last token is a closing brace of blocks.
  const lastToken = sourceCode.getLastToken(node, isNotSemicolonToken)
  const belongingNode
    = lastToken && isClosingBraceToken(lastToken)
      ? sourceCode.getNodeByRangeIndex(lastToken.range[0])
      : null

  return (
    !!belongingNode
    && (belongingNode.type === 'BlockStatement'
      || belongingNode.type === 'SwitchStatement')
  )
}

/**
 * Gets the actual last token.
 *
 * If a semicolon is semicolon-less style's semicolon, this ignores it.
 * For example:
 *
 *     foo()
 *     ;[1, 2, 3].forEach(bar)
 * @param sourceCode The source code to get tokens.
 * @param node The node to get.
 * @returns The actual last token.
 * @private
 */
function getActualLastToken(
  node: ASTNode,
  sourceCode: SourceCode,
): Token | null {
  const semiToken = sourceCode.getLastToken(node)!
  const prevToken = sourceCode.getTokenBefore(semiToken)
  const nextToken = sourceCode.getTokenAfter(semiToken)
  const isSemicolonLessStyle
    = prevToken
      && nextToken
      && prevToken.range[0] >= node.range[0]
      && isSemicolonToken(semiToken)
      && !isTokenOnSameLine(prevToken, semiToken)
      && isTokenOnSameLine(semiToken, nextToken)

  return isSemicolonLessStyle ? prevToken : semiToken
}

function getReportLoc(node: ASTNode, sourceCode: SourceCode): Location {
  if (isSingleLine(node))
    return node.loc

  const line = node.loc.start.line
  const sourceLine = sourceCode.lines[line - 1]
  if (sourceLine === undefined)
    throw new Error('Padding rule invariant: statement source line is missing')

  return {
    start: node.loc.start,
    end: {
      line,
      column: sourceLine.length,
    },
  }
}

/**
 * Check and report statements for `always` configuration.
 * This autofix inserts a blank line between the given 2 statements.
 * If the `prevNode` has trailing comments, it inserts a blank line after the
 * trailing comments.
 * @param context The rule context to report.
 * @param prevNode The previous node to check.
 * @param nextNode The next node to check.
 * @param hasPadding Whether a blank line already separates tokens.
 *
 * @private
 */
function verifyForAlways(
  context: RuleContext,
  prevNode: ASTNode,
  nextNode: ASTNode,
  hasPadding: boolean,
): void {
  if (hasPadding)
    return

  context.report({
    node: nextNode,
    messageId: 'expectedBlankLine',
    loc: getReportLoc(nextNode, context.sourceCode),
    fix(fixer) {
      const sourceCode = context.sourceCode
      let prevToken = getActualLastToken(prevNode, sourceCode)!
      const nextToken
        = sourceCode.getFirstTokenBetween(prevToken, nextNode, {
          includeComments: true,

          /**
           * Skip the trailing comments of the previous node.
           * This inserts a blank line after the last trailing comment.
           *
           * For example:
           *
           *     foo(); // trailing comment.
           *     // comment.
           *     bar();
           *
           * Get fixed to:
           *
           *     foo(); // trailing comment.
           *
           *     // comment.
           *     bar();
           * @param token The token to check.
           * @returns `true` if the token is not a trailing comment.
           * @private
           */
          filter(token) {
            if (isTokenOnSameLine(prevToken, token)) {
              prevToken = token
              return false
            }
            return true
          },
        })! || nextNode
      const insertText = isTokenOnSameLine(prevToken, nextToken)
        ? '\n\n'
        : '\n'

      return fixer.insertTextAfter(prevToken, insertText)
    },
  })
}

// Only matchers used by require-readable-spacing's fixed policy.
const StatementTypes: Record<string, NodeTestObject> = {
  '*': { test: (): boolean => true },
  'block-like': { test: isBlockLikeStatement },
  'function': newNodeTypeTester('FunctionDeclaration'),
  'class': newKeywordTester('ClassDeclaration', 'class'),
  'interface': newKeywordTester('TSInterfaceDeclaration', 'interface'),
  'type': newKeywordTester('TSTypeAliasDeclaration', 'type'),
  'return': newKeywordTester('ReturnStatement', 'return'),
  'do': newKeywordTester('DoWhileStatement', 'do'),
  'for': newKeywordTester(['ForStatement', 'ForInStatement', 'ForOfStatement'], 'for'),
  'if': newKeywordTester('IfStatement', 'if'),
  'import': newKeywordTester('ImportDeclaration', 'import'),
  'switch': newKeywordTester('SwitchStatement', 'switch'),
  'try': newKeywordTester('TryStatement', 'try'),
  'while': newKeywordTester(['WhileStatement', 'DoWhileStatement'], 'while'),
  ...Object.fromEntries(['var', 'let', 'const', 'using'].map(kind => [
    `multiline-${kind}`,
    {
      test: (node: ASTNode, sourceCode: SourceCode) => !isSingleLine(node)
        && (kind === 'using'
          ? node.type === 'VariableDeclaration' && (node.kind === 'using' || node.kind === 'await using')
          : newKeywordTester('VariableDeclaration', kind).test(node, sourceCode)),
    },
  ])),
}

/** Build the vendored padding rule with caller-owned, typed policy options. */
export default function createPaddingLineRule(options: RuleOptions): CreateRule {
return {
  meta: {
    type: 'layout',
    docs: {
      description: 'Require or disallow padding lines between statements',
    },
    fixable: 'whitespace',
    hasSuggestions: false,
    schema: [],
    messages: {
      expectedBlankLine: 'Expected blank line before this statement.',
    },
  },
  create(context) {
    const sourceCode = context.sourceCode

    const selectorMatchedNodes = new Map<string, Set<ASTNode>>()
    const pendingPairs: { prevNode: ASTNode, nextNode: ASTNode }[] = []

    function collectSelectorOption(option: StatementOption): void {
      if (Array.isArray(option)) {
        for (const item of option)
          collectSelectorOption(item)
        return
      }

      if (!isSelectorOption(option))
        return

      selectorMatchedNodes.set(option.selector, new Set())
    }

    for (const configure of options) {
      collectSelectorOption(configure.prev)
      collectSelectorOption(configure.next)
    }

    type Scope = {
      upper: Scope
      prevNode: ASTNode | null
    } | null

    let scopeInfo: Scope = null

    /**
     * Processes to enter to new scope.
     * This manages the current previous statement.
     *
     * @private
     */
    function enterScope(): void {
      scopeInfo = {
        upper: scopeInfo,
        prevNode: null,
      }
    }

    /**
     * Processes to exit from the current scope.
     *
     * @private
     */
    function exitScope(): void {
      if (scopeInfo)
        scopeInfo = scopeInfo.upper
    }

    /**
     * Checks whether the given node matches the given type.
     * @param node The statement node to check.
     * @param type The statement type to check.
     * @returns `true` if the statement node matched the type.
     * @private
     */
    function match(node: ASTNode, type: StatementOption): boolean {
      let innerStatementNode = node

      while (innerStatementNode.type === 'LabeledStatement')
        innerStatementNode = innerStatementNode.body

      if (Array.isArray(type))
        return type.some(match.bind(null, innerStatementNode))

      if (isSelectorOption(type)) {
        const matchedNodes = selectorMatchedNodes.get(type.selector)
        if (!matchedNodes?.has(innerStatementNode))
          return false

        return true
      }
      else {
        const statementType = StatementTypes[type]
        if (statementType === undefined)
          throw new Error(`Padding rule invariant: unsupported statement type ${type}`)
        return statementType.test(innerStatementNode, sourceCode)
      }
    }

    /**
     * Finds the last matched configure from options.
     * @param prevNode The previous statement to match.
     * @param nextNode The current statement to match.
     * @returns Whether the last matching policy requires a blank line.
     * @private
     */
    function needsPadding(
      prevNode: ASTNode,
      nextNode: ASTNode,
    ): boolean {
      for (let i = options.length - 1; i >= 0; --i) {
        const configure = options[i]
        if (configure === undefined)
          throw new Error('Padding rule invariant: configuration entry is missing')
        if (
          match(prevNode, configure.prev)
          && match(nextNode, configure.next)
        ) {
          return configure.blankLine === 'always'
        }
      }
      return false
    }

    /**
     * Finds an existing blank line between statements, treating comments as separators.
     * @param prevNode The previous statement to count.
     * @param nextNode The current statement to count.
     * @returns Whether a blank line already separates tokens.
     * @private
     */
    function hasPaddingLine(
      prevNode: ASTNode,
      nextNode: ASTNode,
    ): boolean {
      let prevToken: Token = getActualLastToken(prevNode, sourceCode)!

      if (nextNode.loc.start.line - prevToken.loc.end.line >= 2) {
        do {
          const token: Token = sourceCode.getTokenAfter(prevToken, {
            includeComments: true,
          })!

          if (token.loc.start.line - prevToken.loc.end.line >= 2)
            return true

          prevToken = token
        } while (prevToken.range[0] < nextNode.range[0])
      }

      return false
    }

    /**
     * Verify padding lines between the given node and the previous node.
     * @param node The node to verify.
     *
     * @private
     */
    function verify(node: ASTNode): void {
      if (
        !node.parent
        || ![
          'BlockStatement',
          'Program',
          'StaticBlock',
          'SwitchCase',
          'SwitchStatement',
          'TSInterfaceBody',
          'TSModuleBlock',
          'TSTypeLiteral',
        ].includes(node.parent.type)
      ) {
        return
      }

      // Save this node as the current previous statement.
      const prevNode = scopeInfo!.prevNode

      // Verify.
      if (prevNode)
        pendingPairs.push({ prevNode, nextNode: node })

      scopeInfo!.prevNode = node
    }

    function verifyPendingPairs(): void {
      for (const { prevNode, nextNode } of pendingPairs) {
        if (needsPadding(prevNode, nextNode))
          verifyForAlways(context, prevNode, nextNode, hasPaddingLine(prevNode, nextNode))
      }
    }

    /**
     * Verify padding lines between the given node and the previous node.
     * Then process to enter to new scope.
     * @param node The node to verify.
     *
     * @private
     */
    function verifyThenEnterScope(node: ASTNode): void {
      verify(node)
      enterScope()
    }

    const selectorMatchListeners = Object.fromEntries(
      Array.from(selectorMatchedNodes.keys(), selector => [
        selector,
        (node: ASTNode): void => {
          selectorMatchedNodes.get(selector)?.add(node)
        },
      ]),
    )

    return {
      'Program': enterScope,
      'Program:exit': () => {
        verifyPendingPairs()
        exitScope()
      },
      'BlockStatement': enterScope,
      'BlockStatement:exit': exitScope,
      'SwitchStatement': enterScope,
      'SwitchStatement:exit': exitScope,
      'SwitchCase': verifyThenEnterScope,
      'SwitchCase:exit': exitScope,
      'StaticBlock': enterScope,
      'StaticBlock:exit': exitScope,

      'TSInterfaceBody': enterScope,
      'TSInterfaceBody:exit': exitScope,
      'TSModuleBlock': enterScope,
      'TSModuleBlock:exit': exitScope,
      'TSTypeLiteral': enterScope,
      'TSTypeLiteral:exit': exitScope,
      'TSDeclareFunction': verifyThenEnterScope,
      'TSDeclareFunction:exit': exitScope,
      'TSMethodSignature': verifyThenEnterScope,
      'TSMethodSignature:exit': exitScope,

      ':statement': verify,
      ...selectorMatchListeners,
    }
  },
}
}
