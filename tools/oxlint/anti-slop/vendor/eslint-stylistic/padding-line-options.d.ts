// Fixed policy subset of the vendored rule; see UPSTREAM.md.
export type StatementType =
  | '*'
  | 'block-like'
  | 'function'
  | 'class'
  | 'interface'
  | 'type'
  | 'return'
  | 'do'
  | 'for'
  | 'if'
  | 'import'
  | 'switch'
  | 'try'
  | 'while'
  | `multiline-${'var' | 'let' | 'const' | 'using'}`

export interface SelectorOption {
  selector: string
}

export type StatementOption =
  | StatementType
  | SelectorOption
  | (StatementType | SelectorOption)[]

export type RuleOptions = {
  blankLine: 'any' | 'always'
  prev: StatementOption
  next: StatementOption
}[]
