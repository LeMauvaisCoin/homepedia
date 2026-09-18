import { defineRule } from "@oxlint/plugins";

import type { ESTree, SourceCode } from "@oxlint/plugins";

type TypeAssertion = ESTree.TSAsExpression | ESTree.TSTypeAssertion;

const SAFETY_COMMENT = /(?:^|[^\p{L}\p{N}_])SAFETY\s*:\s*\S/u;

const commentOwnerKinds = new Set([
  "ExpressionStatement",
  "PropertyDefinition",
  "ReturnStatement",
  "ThrowStatement",
  "VariableDeclaration",
]);

function isConstAssertion(node: TypeAssertion): boolean {
  return (
    node.typeAnnotation.type === "TSTypeReference" &&
    node.typeAnnotation.typeName.type === "Identifier" &&
    node.typeAnnotation.typeName.name === "const"
  );
}

function hasSafetyJustificationBefore(
  sourceCode: SourceCode,
  owner: ESTree.Node,
  assertion: TypeAssertion,
): boolean {
  return sourceCode
    .getCommentsBefore(owner)
    .some(
      (comment) => comment.end <= assertion.start && SAFETY_COMMENT.test(comment.value),
    );
}

function hasSafetyComment(
  sourceCode: SourceCode,
  node: TypeAssertion,
): boolean {
  let current: ESTree.Node = node;
  while (true) {
    if (hasSafetyJustificationBefore(sourceCode, current, node)) return true;
    if (commentOwnerKinds.has(current.type)) {
      const exportDeclaration = current.parent;
      return (
        exportDeclaration.type === "ExportNamedDeclaration" &&
        exportDeclaration.declaration === current &&
        hasSafetyJustificationBefore(sourceCode, exportDeclaration, node)
      );
    }
    if (current.parent.type === "Program") return false;
    current = current.parent;
  }
}

/** Require every non-const type assertion to state the invariant TypeScript cannot express. */
export const requireSafetyCommentForTypeAssertionRule = defineRule({
  meta: {
    type: "problem",
    docs: {
      description:
        "Require a nearby SAFETY comment for every TypeScript type assertion except const assertions.",
    },
    messages: {
      missingSafetyComment:
        "This type assertion has no `{{marker}}:` justification. State the checked invariant immediately before the assertion or its containing statement.",
    },
    schema: [],
  },
  createOnce(context) {
    const checkAssertion = (node: TypeAssertion) => {
      if (isConstAssertion(node)) return;
      if (hasSafetyComment(context.sourceCode, node)) return;
      context.report({
        node,
        messageId: "missingSafetyComment",
        data: { marker: "SAFETY" },
      });
    };

    return {
      TSAsExpression: checkAssertion,
      TSTypeAssertion: checkAssertion,
    };
  },
});
