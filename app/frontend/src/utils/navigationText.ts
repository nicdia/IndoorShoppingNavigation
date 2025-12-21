import { RouteNode } from "../types/route";

type ProductStop = {
  productId: number;
  productName: string;
  nodeId: string;
  level?: number | null;
};

type NodeProductEntry = {
  productId: number | null;
  productName: string;
  position?: { x: number; y: number };
};

type NavigationOptions = {
  path: RouteNode[];
  routeItems: ProductStop[];
  nodeProductMap: Map<string, NodeProductEntry[]>;
  resolveNodeName: (nodeId: string) => string;
};

type TurnDirection = "left" | "right" | "back" | "straight";
type MovementResult = {
  sentences: string[];
  trailingDistance: number;
  lastHeading?: { x: number; y: number };
};

const METRIC_PRECISION = 1;
const MIN_SEGMENT_LENGTH = 0.05;
const STRAIGHT_ANGLE_THRESHOLD = (20 * Math.PI) / 180;
const UTURN_ANGLE_THRESHOLD = (150 * Math.PI) / 180;
const PRODUCT_BRANCH_THRESHOLD = 1.5;

export function buildNavigationInstructions({
  path,
  routeItems,
  nodeProductMap,
  resolveNodeName,
}: NavigationOptions): string[] {
  if (path.length === 0 || routeItems.length === 0) {
    return [];
  }

  const instructions: string[] = [];
  const productUsage = new Map<string, number>();
  let cursorIndex = 0;
  let lastHeading: { x: number; y: number } | undefined;

  const startLabel = resolveNodeName(path[0].nodeId);
  const startSentence = startLabel && startLabel !== path[0].nodeId ? `Start at ${startLabel}.` : null;

  routeItems.forEach((item, itemIndex) => {
    const targetIndex = findNextOccurrence(path, item.nodeId, cursorIndex);
    if (targetIndex === -1) {
      const anchorIndex = Math.min(cursorIndex, Math.max(path.length - 1, 0));
      const anchorNode = path[anchorIndex];
      if (!anchorNode) {
        const fallbackLabel = resolveNodeName(item.nodeId);
        instructions.push(`${item.productName} is located at ${fallbackLabel}.`);
        return;
      }

      const previousNode = anchorIndex > 0 ? path[anchorIndex - 1] : undefined;
      const nextNode = anchorIndex < path.length - 1 ? path[anchorIndex + 1] : undefined;

      const productNarration = buildProductNarration({
        item,
        approachNode: anchorNode,
        incomingNode: previousNode,
        productNode: anchorNode,
        outgoingNode: nextNode,
        nodeProductMap,
        productUsage,
      });

      const sentences: string[] = [];
      if (itemIndex === 0 && startSentence) {
        sentences.push(startSentence);
      }
      if (productNarration) {
        sentences.push(productNarration);
      } else {
        const fallbackLabel = resolveNodeName(item.nodeId);
        sentences.push(`${item.productName} is located at ${fallbackLabel}.`);
      }
      if (sentences.length > 0) {
        instructions.push(sentences.join(" "));
      }
      return;
    }

    const approachIndex = targetIndex > 0 ? targetIndex - 1 : targetIndex;
    const approachNode = approachIndex >= 0 ? path[approachIndex] : undefined;
    const productNode = path[targetIndex];
    const branchDistance = approachNode ? distanceBetween(approachNode, productNode) : Number.POSITIVE_INFINITY;
    const hasProductBranch =
      Boolean(approachNode) && targetIndex > cursorIndex && branchDistance <= PRODUCT_BRANCH_THRESHOLD;

    const rawMovementEnd = hasProductBranch ? targetIndex : targetIndex + 1;
    const movementEnd = Math.min(Math.max(rawMovementEnd, cursorIndex + 1), path.length);
    const movementPath = targetIndex === cursorIndex ? [path[targetIndex]] : path.slice(cursorIndex, movementEnd);
    const movement = buildMovementSentences(
      movementPath,
      cursorIndex > 0 ? path[cursorIndex - 1] : undefined,
      lastHeading
    );

    const incomingNode =
      movementPath.length >= 2
        ? movementPath[movementPath.length - 2]
        : approachIndex > 0
        ? path[approachIndex - 1]
        : undefined;

    const nextAfterProduct = path[targetIndex + 1];
    let outgoingNode: RouteNode | undefined;
    let resumeIndex = targetIndex;

    if (hasProductBranch && nextAfterProduct && approachNode && nextAfterProduct.nodeId === approachNode.nodeId) {
      outgoingNode = path[targetIndex + 2];
      resumeIndex = targetIndex + 1;
    } else {
      outgoingNode = nextAfterProduct;
      resumeIndex = targetIndex;
    }

    const productNarration = buildProductNarration({
      item,
      approachNode,
      incomingNode,
      productNode,
      outgoingNode,
      nodeProductMap,
      productUsage,
    });

    const sentences: string[] = [];

    if (itemIndex === 0 && startSentence) {
      sentences.push(startSentence);
    }

    sentences.push(...movement.sentences);
    if (movement.trailingDistance >= 2) {
      sentences.push(`${buildStraightInstruction(movement.trailingDistance)}.`);
    }
    if (productNarration) {
      sentences.push(productNarration);
    }

    if (sentences.length > 0) {
      instructions.push(sentences.join(" "));
    }
    lastHeading = movement.lastHeading ?? lastHeading;
    cursorIndex = Math.max(resumeIndex, cursorIndex);
  });

  if (cursorIndex <= path.length - 1) {
    const remainingPath = path.slice(cursorIndex, path.length);
    const previousNode = cursorIndex > 0 ? path[cursorIndex - 1] : undefined;
    const finalMovement = buildMovementSentences(remainingPath, previousNode, lastHeading);

    const finalSentences: string[] = [];
    finalSentences.push(...finalMovement.sentences);
    if (finalMovement.trailingDistance >= 2) {
      finalSentences.push(`${buildStraightInstruction(finalMovement.trailingDistance)}.`);
    }

    const destinationNode = path[path.length - 1];
    const destinationLabel = resolveNodeName(destinationNode.nodeId);
    const destinationDescription =
      destinationLabel && destinationLabel !== destinationNode.nodeId ? destinationLabel : "the checkout";
    finalSentences.push(`Finish at ${destinationDescription}.`);

    const finalText = finalSentences.join(" ").trim();
    if (finalText) {
      instructions.push(finalText);
    }
    lastHeading = finalMovement.lastHeading ?? lastHeading;
  }

  return instructions;
}

function buildProductNarration({
  item,
  approachNode,
  incomingNode,
  productNode,
  outgoingNode,
  nodeProductMap,
  productUsage,
}: {
  item: ProductStop;
  approachNode?: RouteNode;
  incomingNode?: RouteNode;
  productNode: RouteNode;
  outgoingNode?: RouteNode;
  nodeProductMap: Map<string, NodeProductEntry[]>;
  productUsage: Map<string, number>;
}): string | null {
  const { productId, productName, nodeId, level } = item;
  const candidates = nodeProductMap.get(nodeId) ?? [];
  const usage = productUsage.get(nodeId) ?? 0;

  const candidate = findMatchingProductCandidate({ productId, productName, candidates, usage });

  const side = determineProductSide({
    incomingNode,
    approachNode,
    productNode,
    outgoingNode,
    productPosition: candidate?.position,
  });
  const shelf = describeShelf(level);

  productUsage.set(nodeId, usage + 1);
  const shelfPreposition = "in the";
  return `${productName} is ${describeSide(side)} ${shelfPreposition} ${shelf}.`;
}

function findMatchingProductCandidate({
  productId,
  productName,
  candidates,
  usage,
}: {
  productId: number;
  productName: string;
  candidates: NodeProductEntry[];
  usage: number;
}) {
  return (
    candidates.find((entry) => entry.productId !== null && entry.productId === productId) ??
    candidates.find((entry) => entry.productName === productName) ??
    candidates[usage]
  );
}

function buildMovementSentences(
  segmentPath: RouteNode[],
  previousNode?: RouteNode,
  initialHeading?: { x: number; y: number }
) : MovementResult {
  if (segmentPath.length <= 1) {
    return { sentences: [], trailingDistance: 0, lastHeading: initialHeading };
  }

  const sentences: string[] = [];
  let accumulatedDistance = 0;
  let lastHeading =
    initialHeading ?? (previousNode && segmentPath.length > 0 ? vectorBetween(previousNode, segmentPath[0]) : undefined);

  for (let index = 1; index < segmentPath.length; index += 1) {
    const previous = segmentPath[index - 1];
    const current = segmentPath[index];
    const segmentDistance = distanceBetween(previous, current);

    if (segmentDistance < MIN_SEGMENT_LENGTH) {
      continue;
    }

    const heading = vectorBetween(previous, current);
    if (lastHeading && heading) {
      const turn = classifyTurnFromVectors(lastHeading, heading);
      if (turn !== "straight") {
        if (accumulatedDistance > 0) {
          const straightText = buildStraightInstruction(accumulatedDistance);
          const turnText = buildTurnInstruction(turn);
          sentences.push(`${straightText}, then ${turnText}.`);
          accumulatedDistance = 0;
        } else {
          sentences.push(`${capitalizeFirst(buildTurnInstruction(turn))}.`);
        }
      }
    }

    accumulatedDistance += segmentDistance;
    lastHeading = heading ?? lastHeading;

    const isLastSegment = index === segmentPath.length - 1;

    if (!isLastSegment) {
      // continue to evaluate upcoming turn with updated heading
      continue;
    }
  }

  return { sentences, trailingDistance: accumulatedDistance, lastHeading };
}

function findNextOccurrence(path: RouteNode[], targetNodeId: string, startIndex: number) {
  for (let index = startIndex; index < path.length; index += 1) {
    if (path[index].nodeId === targetNodeId) {
      return index;
    }
  }
  return -1;
}

function buildStraightInstruction(distanceMeters: number) {
  return `Walk ${formatMeters(distanceMeters)} meters straight ahead`;
}

function buildTurnInstruction(turn: TurnDirection) {
  switch (turn) {
    case "left":
      return "turn left";
    case "right":
      return "turn right";
    case "back":
      return "make a U-turn";
    default:
      return "continue straight";
  }
}

function determineProductSide({
  incomingNode,
  approachNode,
  productNode,
  outgoingNode,
  productPosition,
}: {
  incomingNode?: RouteNode;
  approachNode?: RouteNode;
  productNode: RouteNode;
  outgoingNode?: RouteNode;
  productPosition?: { x: number; y: number };
}): "left" | "right" | "ahead" {
  const anchor = approachNode ?? productNode;

  const forwardVector =
    (incomingNode && approachNode ? vectorBetween(incomingNode, approachNode) : undefined) ??
    (approachNode && outgoingNode ? vectorBetween(approachNode, outgoingNode) : undefined) ??
    (approachNode ? vectorBetween(approachNode, productNode) : undefined) ??
    (productPosition ? { x: productPosition.x - anchor.x, y: productPosition.y - anchor.y } : undefined);

  let sideVector: { x: number; y: number } | undefined;

  if (productPosition) {
    sideVector = { x: productPosition.x - anchor.x, y: productPosition.y - anchor.y };
  } else if (approachNode) {
    sideVector = vectorBetween(approachNode, productNode);
  } else if (outgoingNode) {
    sideVector = vectorBetween(anchor, outgoingNode);
  }

  const heading = forwardVector ? normalizeVector(forwardVector) : undefined;
  const lateral = sideVector ? normalizeVector(sideVector) : undefined;

  if (!heading || !lateral) {
    return "ahead";
  }

  const cross = heading.x * lateral.y - heading.y * lateral.x;
  if (Math.abs(cross) < 1e-3) {
    return "ahead";
  }

  return cross > 0 ? "left" : "right";
}

function describeSide(side: "left" | "right" | "ahead") {
  switch (side) {
    case "left":
      return "on the left side";
    case "right":
      return "on the right side";
    default:
      return "straight ahead";
  }
}

function describeShelf(level?: number | null) {
  switch (level) {
    case 1:
      return "upper shelf";
    case 2:
      return "middle shelf";
    case 3:
      return "lower shelf";
    default:
      return "shelf";
  }
}

function normalizeVector(vector: { x: number; y: number }) {
  const length = Math.hypot(vector.x, vector.y);
  if (length === 0) {
    return undefined;
  }
  return {
    x: vector.x / length,
    y: vector.y / length,
  };
}

function distanceBetween(a: RouteNode, b: RouteNode) {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

function vectorBetween(from?: RouteNode, to?: RouteNode) {
  if (!from || !to) {
    return undefined;
  }
  return { x: to.x - from.x, y: to.y - from.y };
}

function classifyTurnFromVectors(
  incoming: { x: number; y: number } | undefined,
  outgoing: { x: number; y: number } | undefined
): TurnDirection {
  const inNorm = incoming ? normalizeVector(incoming) : undefined;
  const outNorm = outgoing ? normalizeVector(outgoing) : undefined;

  if (!inNorm || !outNorm) {
    return "straight";
  }

  const dotProduct = clamp(inNorm.x * outNorm.x + inNorm.y * outNorm.y, -1, 1);
  const angle = Math.acos(dotProduct);

  if (angle < STRAIGHT_ANGLE_THRESHOLD) {
    return "straight";
  }

  if (angle > UTURN_ANGLE_THRESHOLD) {
    return "back";
  }

  const crossProduct = inNorm.x * outNorm.y - inNorm.y * outNorm.x;
  return crossProduct > 0 ? "left" : "right";
}

function formatMeters(distance: number) {
  return distance.toFixed(METRIC_PRECISION).replace(/\.0$/, "");
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function capitalizeFirst(value: string) {
  if (!value) {
    return value;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}
