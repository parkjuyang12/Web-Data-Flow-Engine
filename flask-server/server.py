from flask import Flask, request, jsonify
from antlr4 import *
from HTMLLexer import HTMLLexer
from HTMLParser import HTMLParser
from neo4j import GraphDatabase
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)


# Neo4j connection setup
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "juyang"
NEO4J_PASSWORD = "qkrwndid11!"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

class HTMLParserMain:
    def parse_html(self, html_text):
        input_stream = InputStream(html_text)
        lexer = HTMLLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = HTMLParser(stream)
        tree = parser.htmlDocument()
        return self._convert_tree_to_dict(tree)

    def _convert_tree_to_dict(self, tree):
        def traverse(node):
            if isinstance(node, TerminalNode):
                return {"text": node.getText()}

            result = {"tag": node.getText()}
            children = []
            for i in range(node.getChildCount()):
                child = node.getChild(i)
                child_dict = traverse(child)
                if child_dict:
                    children.append(child_dict)
            if children:
                result["children"] = children
            return result

        return traverse(tree)

# Clean text function to avoid issues with Neo4j parsing errors
def clean_text_for_neo4j(text):
    return re.sub(r'[^a-zA-Z0-9ㄱ-ㅣ가-힣]', '', text)

# Convert attributes with hyphens to underscores
def convert_hyphens_to_underscores(attributes):
    return {key.replace('-', '_'): value for key, value in attributes.items()}

# Function to create elements in Neo4j
def create_element(tx, tag_name, parent=None, text=None, attributes=None):
    if not tag_name:
        return  # Skip if tag_name is None or empty
    
    if attributes:
        attributes = convert_hyphens_to_underscores(attributes)
    
    query = "MERGE (e:Element {tag: $tag_name})"
    parameters = {'tag_name': tag_name}
    
    if attributes:
        for attr, value in attributes.items():
            query += f" SET e.{attr} = ${attr}"
            parameters[attr] = value
    
    tx.run(query, **parameters)
    
    if parent:
        tx.run("""
        MATCH (p:Element {tag: $parent_tag})
        MATCH (e:Element {tag: $tag_name})
        MERGE (p)-[:CONTAINS]->(e)
        """, parent_tag=parent, tag_name=tag_name)

    if text:
        tx.run("""
        MATCH (e:Element {tag: $tag_name})
        MERGE (t:Text {content: $text})
        MERGE (e)-[:HAS_TEXT]->(t)
        """, tag_name=tag_name, text=text)

# Function to parse and insert HTML data into Neo4j
def insert_html_data_into_neo4j(parsed_tree):
    def traverse_and_store(node, parent=None):
        tag = node.get("tag")
        if tag is None:
            return  # Skip if tag is None
        
        text = node.get("text")
        attributes = node.get("attributes", {})
        with driver.session() as session:
            session.write_transaction(create_element, tag, parent, text, attributes)
            for child in node.get("children", []):
                traverse_and_store(child, tag)

    traverse_and_store(parsed_tree)

@app.route('/analyze', methods=['POST'])
def analyze_html():
    data = request.json
    html_text = data.get('html', '')
    title = data.get('title', '')
    date = data.get('date', '')
    media = data.get('media', '')
    keyword = data.get('keyword', [])

    parser = HTMLParserMain()
    parsed_tree = parser.parse_html(html_text)

    clean_title = clean_text_for_neo4j(title)
    
    insert_html_data_into_neo4j(parsed_tree)

    return jsonify({'parsed_tree': parsed_tree})

@app.route('/fetch-data', methods=['GET'])
def fetch_data():
    query_nodes = """
    MATCH (n) RETURN n
    """
    query_edges = """
    MATCH (n)-[r]->(m) RETURN n, r, m
    """
    
    with driver.session() as session:
        result_nodes = session.run(query_nodes)
        result_edges = session.run(query_edges)

        nodes = []
        edges = []

        for record in result_nodes:
            node = record['n']
            nodes.append({
                'id': node.id,
                'label': node['tag'] if 'tag' in node else 'unknown'
            })

        for record in result_edges:
            start_node = record['n']
            end_node = record['m']
            rel = record['r']

            edges.append({
                'data': {
                    'id': '{}-{}'.format(start_node.id, end_node.id),
                    'source': start_node.id,
                    'target': end_node.id,
                    'label': rel.type
                }
            })

        return jsonify({'nodes': nodes, 'edges': edges})


if __name__ == '__main__':
    app.run(debug=True, port=5002)
