import matplotlib.pyplot as plt
import igraph as ig
import sys

'''
Class that represents a node in the graph
A node can have children if it is a directory
Its children are other nodes
'''
class TreeNode:
    def __init__(self, name, isDirectory=False, children=None, httpCode="", size=""):
        self.name = name
        self.isDirectory = isDirectory
        self.children = children if children is not None else []
        self.httpCode = httpCode
        self.size = size

    def addChild(self, child):
        self.children.append(child)

############ UTILS #############

# Extracts object name, HTTP code and size from a "+ URL (CODE:xxx|SIZE:xxx)" line
def parseObjectInfo(file_line):
    cleaned_string = file_line.strip().lstrip("+ ")
    parts = cleaned_string.split(" (CODE:")
    name = parts[0].rsplit("/", 1)[-1]
    code, size = parts[1].rstrip(")").split("|SIZE:")
    return name, code, size

# Extracts full directory URL from a "==> DIRECTORY: URL" line
def parseDirectoryUrl(dir_line):
    return dir_line.split("==> DIRECTORY: ", 1)[1].strip()

# Extracts short directory name from a full URL
def parseDirShortName(url):
    return url.rstrip("/").rsplit("/", 1)[-1] + "/"

# Extracts URL from a "---- Entering directory: URL ----" line
def parseEnteringDirUrl(line):
    return line.split("---- Entering directory: ", 1)[1].replace(" ----", "").strip()

# Check if current line is a sub-directory
def detectDir(string):
    return "==> DIRECTORY:" in string

# Check if current line is a web object
def detectObject(string):
    return string.strip().startswith("+ ")

# Check if current line is entering a new directory section
def detectEnteringDir(string):
    return "---- Entering directory:" in string

# Check if current line is base URL section
def isBaseUrl(string):
    return "URL_BASE:" in string

# Check if current line is pre-scan section
def isAtFirstScan(string):
    return "GENERATED WORDS:" in string

############ PHASE 1: PARSE FILE INTO SECTIONS #############

def parseSections(filename):
    '''
    Reads the DIRB output file linearly and builds a flat dictionary:
    { directory_url: { "objects": [name, ...], "subdirs": [url, ...] } }
    '''
    sections = {}
    base_url = ""

    with open(filename, "rt") as f:
        line = f.readline()

        # Skip header until URL_BASE
        while line and not isBaseUrl(line):
            line = f.readline()
        base_url = line.split("URL_BASE: ", 1)[1].strip()

        # Skip to GENERATED WORDS
        while line and not isAtFirstScan(line):
            line = f.readline()

        # Skip two lines after "GENERATED WORDS" section
        next(f)
        next(f)

        # The first section belongs to the base URL (no "Entering directory" header)
        current_url = base_url
        sections[current_url] = {"objects": [], "subdirs": []}

        for line in f:
            if detectEnteringDir(line):
                current_url = parseEnteringDirUrl(line)
                if current_url not in sections:
                    sections[current_url] = {"objects": [], "subdirs": []}
            elif detectDir(line):
                sections[current_url]["subdirs"].append(parseDirectoryUrl(line))
            elif detectObject(line):
                sections[current_url]["objects"].append(parseObjectInfo(line))

    return base_url, sections

############ PHASE 2: BUILD TREE RECURSIVELY #############

def buildTree(url, sections, shortName=None):
    '''
    Recursively builds a TreeNode tree from the sections dictionary.
    Directories that were listed but never entered (scan stopped early)
    appear as leaf nodes with no children.
    '''
    name = shortName if shortName else url
    node = TreeNode(name=name, isDirectory=True)

    if url in sections:
        for obj_name, code, size in sections[url]["objects"]:
            node.addChild(TreeNode(name=obj_name, isDirectory=False, httpCode=code, size=size))
        for subdir_url in sections[url]["subdirs"]:
            child = buildTree(subdir_url, sections, shortName=parseDirShortName(subdir_url))
            node.addChild(child)

    return node

############ CONVERT TREE TO IGRAPH #############

def treeToGraph(node, graph, edges, parent_id=None):
    '''Walks the TreeNode tree and populates igraph vertices and edges.'''
    vid = graph.vcount()
    graph.add_vertex(name=node.name, is_dir=node.isDirectory,
                     http_code=node.httpCode, size=node.size)

    if parent_id is not None:
        edges.append((parent_id, vid))

    for child in node.children:
        treeToGraph(child, graph, edges, vid)

############ RADIAL LAYOUT #############

def computeRadialLayout(root):
    '''
    Custom radial tree layout where each subtree gets its own angular wedge
    proportional to its leaf count. This guarantees edges never cross between
    subtrees since each parent's children sit entirely within the parent's arc.
    Coords are emitted in pre-order DFS to match treeToGraph vertex indices.
    '''
    import math

    # Cache leaf counts
    leaf_cache = {}

    def countLeaves(node):
        nid = id(node)
        if nid not in leaf_cache:
            if not node.children:
                leaf_cache[nid] = 1
            else:
                leaf_cache[nid] = sum(countLeaves(c) for c in node.children)
        return leaf_cache[nid]

    countLeaves(root)

    coords = []

    def layout(node, depth, angleStart, angleEnd):
        angle = (angleStart + angleEnd) / 2
        radius = depth
        coords.append((radius * math.cos(angle), radius * math.sin(angle)))

        if not node.children:
            return

        total = leaf_cache[id(node)]
        cur = angleStart
        for child in node.children:
            span = (angleEnd - angleStart) * leaf_cache[id(child)] / total
            layout(child, depth + 1, cur, cur + span)
            cur += span

    layout(root, 0, 0, 2 * math.pi)
    return coords

############ PLOTTING #############

def plotGraph(graph, root):
    import math

    coords = computeRadialLayout(root)
    layout = ig.Layout(coords)

    fig, ax = plt.subplots(figsize=(22, 22))

    # Directories in blue, objects in green
    colors = ["#3b8ed0" if d else "#5cb85c" for d in graph.vs["is_dir"]]

    # Plot graph without labels (we add them manually with rotation)
    ig.plot(graph, layout=layout, target=ax, margin=120,
            vertex_size=10, vertex_color=colors,
            vertex_label=None,
            edge_width=0.4, edge_arrow_size=0.4, edge_arrow_width=0.4)

    # Add radially-oriented labels
    for i, (x, y) in enumerate(coords):
        if i == 0:
            # Root label at center
            ax.text(x, y - 0.15, graph.vs[i]["name"],
                    fontsize=6, ha="center", va="top", fontweight="bold")
            continue
        angle = math.atan2(y, x)
        deg = math.degrees(angle)
        # Flip labels on left side so they stay readable
        ha = "left" if -90 <= deg <= 90 else "right"
        rot = deg if -90 <= deg <= 90 else deg + 180
        ax.text(x, y, "  " + graph.vs[i]["name"] + "  ",
                fontsize=5, ha=ha, va="center",
                rotation=rot, rotation_mode="anchor")

    # Legend
    from matplotlib.patches import Patch
    legend_items = [Patch(facecolor="#3b8ed0", label="Directory"),
                    Patch(facecolor="#5cb85c", label="Object")]
    ax.legend(handles=legend_items, loc="upper left", fontsize=10)

    plt.title("DIRB Scan Graph", fontsize=14)
    plt.tight_layout()

    # Hover tooltip showing HTTP response code
    annot = ax.annotate("", xy=(0, 0), xytext=(12, 12),
                        textcoords="offset points",
                        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="gray", alpha=0.95),
                        fontsize=8)
    annot.set_visible(False)

    # Compute a hover threshold from the layout scale
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1)
    threshold = (span * 0.012) ** 2

    def on_hover(event):
        if event.inaxes != ax:
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()
            return

        closest = -1
        min_dist = float("inf")
        for i, (cx, cy) in enumerate(coords):
            dist = (cx - event.xdata) ** 2 + (cy - event.ydata) ** 2
            if dist < min_dist:
                min_dist = dist
                closest = i

        if min_dist < threshold and closest >= 0:
            v = graph.vs[closest]
            annot.xy = coords[closest]
            if v["is_dir"]:
                text = f"{v['name']}\nType: Directory"
            else:
                text = f"{v['name']}\nHTTP {v['http_code']}\nSize: {v['size']} B"
            annot.set_text(text)
            annot.set_visible(True)
        else:
            annot.set_visible(False)

        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_hover)
    plt.show()

############ MAIN #############

def main():
    filename = sys.argv[1]

    base_url, sections = parseSections(filename)
    root = buildTree(base_url, sections)

    graph = ig.Graph(directed=True)
    edges = []
    treeToGraph(root, graph, edges)
    graph.add_edges(edges)

    plotGraph(graph, root)

if __name__ == "__main__":
    main()
