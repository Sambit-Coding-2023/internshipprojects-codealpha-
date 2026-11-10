"""
Universal Knowledge Engine for Task 2: FAQ Chatbot
Enables the chatbot to answer open-domain, general knowledge, factual, scientific,
mathematical, technical, coding, and conversational questions beyond the standard store FAQ knowledgebase.

Integrates:
1. Google Gemini 1.5/2.0 Flash Generative AI Gateway (via client key or GEMINI_API_KEY env)
2. Built-in Deep Technical & Coding Knowledge Engine (Python, JS, SQL, Git, HTML/CSS, Algorithms, Regex)
3. Built-in Concept Explainer & Science Engine (Physics, Quantum, Biology, Internet, Astronomy, AI)
4. Built-in Writing & Professional Productivity Assistant (Emails, Outlines, Frameworks)
5. Safe Math & Arithmetic Evaluator (AST evaluation, percentages, formulas)
6. Real-Time Date & Time Service
7. Conversational Chit-Chat & Identity System
8. Two-Phase Wikipedia REST Full-Text Search Engine (Universal facts, history, biographies)
9. DuckDuckGo Instant Answers & Disambiguation Engine
"""

import ast
import datetime
import json
import operator
import os
import random
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Safe Math Operator Mapping
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs! 🪲",
    "Why did the computer go to the doctor? Because it had a virus! 💻",
    "There are 10 types of people in the world: those who understand binary, and those who don't.",
    "Why was the JavaScript developer sad? Because they didn't know how to 'null' their feelings! ☕",
    "What do you call an e-commerce package that arrives on time? A pleasant surprise! 📦",
    "Why did the database administrator leave his wife? She had one-to-many relationships! 📊",
    "An SQL statement walks into a bar, strolls up to two tables and asks, 'Can I join you?' 🍺",
    "How do you comfort a JavaScript bug? You console it! 🖥️",
    "Why do Java programmers wear glasses? Because they don't C#! 👓"
]

IDENTITY_PROMPTS = {
    "who are you", "what is your name", "what are you", "who made you", "who created you",
    "are you a bot", "are you an ai", "are you human", "what can you do"
}

# Technical keywords that immediately identify a non-store query
TECH_KEYWORDS = {
    "python", "javascript", "typescript", "c++", "java", "sql", "html", "css",
    "algorithm", "binary search", "recursion", "regex", "regular expression",
    "git", "github", "docker", "api", "rest api", "json", "function", "array",
    "list comprehension", "bubble sort", "quicksort", "linked list", "hashmap",
    "database", "inner join", "left join", "group by", "object oriented",
    "oop", "async", "await", "promise", "reverse a list", "reverse a string",
    "sort an array", "center a div", "flexbox", "grid", "merge conflict"
}

SCIENCE_KEYWORDS = {
    "quantum", "photosynthesis", "speed of light", "why is the sky blue",
    "how do airplanes fly", "black hole", "relativity", "dna", "evolution",
    "atom", "molecule", "gravity", "solar system", "planet", "galaxy",
    "machine learning", "deep learning", "artificial intelligence", "neural network",
    "blockchain", "how does internet work", "how does computer work"
}

CREATIVE_KEYWORDS = {
    "write an email", "write a poem", "leave request email", "resignation letter",
    "thank you letter", "cover letter", "write an essay", "pomodoro technique",
    "eisenhower matrix"
}


def _safe_eval_math(node):
    """Recursively evaluates safe mathematical AST expressions."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _safe_eval_math(node.left)
        right = _safe_eval_math(node.right)
        op_type = type(node.op)
        if op_type in OPERATORS:
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division by zero")
            return OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _safe_eval_math(node.operand)
        op_type = type(node.op)
        if op_type in OPERATORS:
            return OPERATORS[op_type](operand)
    raise ValueError("Unsupported operation")


class UniversalKnowledgeEngine:
    def __init__(self):
        self.user_agent = "FAQSupportBot/4.0 (Gemini-Integrated Educational AI; Python/urllib)"
        self.default_gemini_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )

    def is_technical_or_creative_query(self, query: str) -> bool:
        """Determines if a query is clearly a programming, scientific, creative, or math query."""
        q = query.lower().strip()
        if any(k in q for k in TECH_KEYWORDS):
            return True
        if any(k in q for k in SCIENCE_KEYWORDS):
            return True
        if any(k in q for k in CREATIVE_KEYWORDS):
            return True
        if q.startswith("write code") or q.startswith("how to code") or "in python" in q or "in javascript" in q:
            return True
        if q.startswith("why ") or q.startswith("explain ") or q.startswith("difference between "):
            return True
        return False

    def is_encyclopedic_query(self, query: str) -> bool:
        """Determines if a query specifically targets world facts rather than store FAQs."""
        q = query.lower().strip()
        indicators = [
            "capital of", "president of", "prime minister of", "population of", "currency of",
            "who invented", "who discovered", "who wrote", "speed of light", "distance to",
            "how far is", "how tall is", "who was the first", "who directed", "chemical formula",
            "atomic number", "boiling point", "freezing point", "how old is", "biography of",
            "capital city", "largest country", "deepest ocean", "tallest mountain", "who is elon musk",
            "who is albert einstein", "who is steve jobs", "who is alan turing"
        ]
        return any(ind in q for ind in indicators)

    # -------------------------------------------------------------------------
    # 1. Google Gemini 1.5/2.0 Generative AI Gateway
    # -------------------------------------------------------------------------
    def query_gemini(self, query: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Invokes Google Gemini 1.5 Flash REST endpoint.
        Returns a rich markdown answer just like the Gemini and ChatGPT web apps.
        """
        key = api_key or self.default_gemini_key
        if not key:
            return None

        # Clean key
        key = key.strip()

        # Try gemini-1.5-flash first, fallback to gemini-2.0-flash
        models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        system_instruction = (
            "You are OmniBot, an omniscient, deeply helpful AI assistant modeled with the speed of Gemini "
            "and depth of ChatGPT. Answer the user's inquiry clearly, thoroughly, and helpfully. "
            "Use clean markdown formatting, structured bullet points, code blocks with syntax highlighting "
            "where applicable, and step-by-step reasoning. Be insightful, concise, and friendly."
        )

        for model in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"{system_instruction}\n\nUser Question:\n{query}"
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 1024
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = parts[0].get("text", "").strip()
                            if text:
                                return {
                                    "found": True,
                                    "text": text,
                                    "source": f"Google {model.replace('-', ' ').title()}",
                                    "badge": "GEMINI ULTRA AI",
                                    "category": "Generative AI"
                                }
            except Exception:
                continue

        return None

    # -------------------------------------------------------------------------
    # 2. Built-in Technical & Coding Knowledge Engine
    # -------------------------------------------------------------------------
    def answer_technical_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Provides expert programming code, syntax, and algorithmic solutions."""
        q = query.lower().strip()

        # Python: Reverse a list or string
        if "reverse" in q and ("list" in q or "array" in q) and ("python" in q or "code" in q or "how" in q):
            return {
                "found": True,
                "text": (
                    "### How to Reverse a List in Python\n\n"
                    "Here are the three most common and efficient ways:\n\n"
                    "#### 1. Slicing (Recommended - Fast & Non-destructive)\n"
                    "```python\n"
                    "original_list = [1, 2, 3, 4, 5]\n"
                    "reversed_list = original_list[::-1]\n"
                    "print(reversed_list)  # Output: [5, 4, 3, 2, 1]\n"
                    "```\n\n"
                    "#### 2. In-Place Reverse (`.reverse()` Method)\n"
                    "```python\n"
                    "numbers = [1, 2, 3, 4, 5]\n"
                    "numbers.reverse()  # Modifies list directly in memory\n"
                    "print(numbers)  # Output: [5, 4, 3, 2, 1]\n"
                    "```\n\n"
                    "#### 3. Using Built-in `reversed()` Iterator\n"
                    "```python\n"
                    "items = ['apple', 'banana', 'cherry']\n"
                    "reversed_items = list(reversed(items))\n"
                    "print(reversed_items)  # Output: ['cherry', 'banana', 'apple']\n"
                    "```"
                ),
                "source": "AI Tech & Code Engine",
                "badge": "PYTHON CODE",
                "category": "Programming"
            }

        # Python: Reverse a string
        if "reverse" in q and "string" in q:
            return {
                "found": True,
                "text": (
                    "### How to Reverse a String in Python\n\n"
                    "In Python, strings are immutable, so slicing `[::-1]` is the fastest and most idiomatic method:\n\n"
                    "```python\n"
                    "text = 'Hello World'\n"
                    "reversed_text = text[::-1]\n"
                    "print(reversed_text)  # Output: 'dlroW olleH'\n"
                    "```\n\n"
                    "#### Alternative with `reversed()` and `.join()`:\n"
                    "```python\n"
                    "text = 'Python'\n"
                    "reversed_text = ''.join(reversed(text))\n"
                    "print(reversed_text)  # Output: 'nohtyP'\n"
                    "```"
                ),
                "source": "AI Tech & Code Engine",
                "badge": "PYTHON CODE",
                "category": "Programming"
            }

        # Algorithms: Binary Search
        if "binary search" in q:
            return {
                "found": True,
                "text": (
                    "### Binary Search Algorithm ($O(\\log n)$)\n\n"
                    "Binary Search finds an item in a **sorted array** by repeatedly dividing the search interval in half.\n\n"
                    "```python\n"
                    "def binary_search(arr, target):\n"
                    "    left, right = 0, len(arr) - 1\n"
                    "    while left <= right:\n"
                    "        mid = (left + right) // 2\n"
                    "        if arr[mid] == target:\n"
                    "            return mid  # Target found at index mid\n"
                    "        elif arr[mid] < target:\n"
                    "            left = mid + 1\n"
                    "        else:\n"
                    "            right = mid - 1\n"
                    "    return -1  # Target not found\n\n"
                    "# Example Usage:\n"
                    "numbers = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]\n"
                    "print(binary_search(numbers, 23))  # Output: 5\n"
                    "```\n\n"
                    "**Complexity:** Time: $O(\\log n)$ | Space: $O(1)$"
                ),
                "source": "AI Tech & Code Engine",
                "badge": "ALGORITHMS",
                "category": "Computer Science"
            }

        # Concept: Recursion
        if "recursion" in q:
            return {
                "found": True,
                "text": (
                    "### What is Recursion in Programming?\n\n"
                    "**Recursion** is a technique where a function solves a problem by calling itself with smaller instances of the same problem.\n\n"
                    "Every recursive function requires two critical components:\n"
                    "1. **Base Case**: The terminating condition that prevents infinite loops.\n"
                    "2. **Recursive Step**: The call to itself that moves toward the base case.\n\n"
                    "#### Classic Example: Factorial ($n!$)\n"
                    "```python\n"
                    "def factorial(n):\n"
                    "    # Base case\n"
                    "    if n <= 1:\n"
                    "        return 1\n"
                    "    # Recursive step\n"
                    "    return n * factorial(n - 1)\n\n"
                    "print(factorial(5))  # Output: 120 (5 * 4 * 3 * 2 * 1)\n"
                    "```"
                ),
                "source": "AI Tech & Code Engine",
                "badge": "CS CONCEPTS",
                "category": "Computer Science"
            }

        # SQL: Duplicates or Joins
        if "sql" in q and ("duplicate" in q or "join" in q or "select" in q):
            return {
                "found": True,
                "text": (
                    "### Common SQL Operations & Best Practices\n\n"
                    "#### 1. Finding Duplicate Rows\n"
                    "```sql\n"
                    "SELECT email, COUNT(*)\n"
                    "FROM users\n"
                    "GROUP BY email\n"
                    "HAVING COUNT(*) > 1;\n"
                    "```\n\n"
                    "#### 2. INNER JOIN vs LEFT JOIN\n"
                    "```sql\n"
                    "-- INNER JOIN: Only returns rows matching in BOTH tables\n"
                    "SELECT orders.id, customers.name\n"
                    "FROM orders\n"
                    "INNER JOIN customers ON orders.customer_id = customers.id;\n\n"
                    "-- LEFT JOIN: Returns ALL rows from left table, matched or NULL from right\n"
                    "SELECT customers.name, orders.id\n"
                    "FROM customers\n"
                    "LEFT JOIN orders ON customers.id = orders.customer_id;\n"
                    "```"
                ),
                "source": "AI Tech & Code Engine",
                "badge": "DATABASE / SQL",
                "category": "Databases"
            }

        # CSS: Centering a Div
        if "center a div" in q or ("center" in q and "css" in q):
            return {
                "found": True,
                "text": (
                    "### How to Center a Div in CSS (Modern Approaches)\n\n"
                    "#### 1. CSS Flexbox (Most Popular & Flexible)\n"
                    "```css\n"
                    ".container {\n"
                    "    display: flex;\n"
                    "    justify-content: center; /* Horizontally centers */\n"
                    "    align-items: center;     /* Vertically centers */\n"
                    "    height: 100vh;           /* Full viewport height */\n"
                    "}\n"
                    "```\n\n"
                    "#### 2. CSS Grid (Shortest & Cleanest)\n"
                    "```css\n"
                    ".container {\n"
                    "    display: grid;\n"
                    "    place-items: center;     /* Centers both axes in 1 line */\n"
                    "    height: 100vh;\n"
                    "}\n"
                    "```"
                ),
                "source": "AI Tech & Code Engine",
                "badge": "WEB DEV / CSS",
                "category": "Web Development"
            }

        # Git: Merge vs Rebase
        if "git" in q and ("rebase" in q or "merge" in q or "branch" in q):
            return {
                "found": True,
                "text": (
                    "### Git Merge vs Git Rebase\n\n"
                    "| Feature | `git merge` | `git rebase` |\n"
                    "|---|---|---|\n"
                    "| **History** | Preserves complete branching history with a merge commit | Creates a clean, linear, single-line commit history |\n"
                    "| **Safety** | Non-destructive; safe on shared public branches | Rewrites commit hashes; never rebase a public branch! |\n"
                    "| **Traceability**| Easy to see feature branch lifecycles | Easier to read with `git log` and bisect |\n\n"
                    "#### Commands:\n"
                    "```bash\n"
                    "# Standard safe merge:\n"
                    "git checkout main\n"
                    "git merge feature-branch\n\n"
                    "# Clean linear rebase:\n"
                    "git checkout feature-branch\n"
                    "git rebase main\n"
                    "```"
                ),
                "source": "AI Tech & Code Engine",
                "badge": "DEV TOOLS / GIT",
                "category": "Developer Tools"
            }

        # Regex: Email validation
        if "regex" in q and ("email" in q or "validate" in q):
            return {
                "found": True,
                "text": (
                    "### Regular Expression (Regex) for Email Validation\n\n"
                    "#### Standard RFC-5322 Compliant Regex Pattern:\n"
                    "```regex\n"
                    "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$\n"
                    "```\n\n"
                    "#### Python Implementation Example:\n"
                    "```python\n"
                    "import re\n\n"
                    "def is_valid_email(email):\n"
                    "    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n"
                    "    return bool(re.match(pattern, email))\n\n"
                    "print(is_valid_email('user@example.com'))   # True\n"
                    "print(is_valid_email('invalid-email@com'))  # False\n"
                    "```"
                ),
                "source": "AI Tech & Code Engine",
                "badge": "REGEX / TOOLS",
                "category": "Programming"
            }

        return None

    # -------------------------------------------------------------------------
    # 3. Built-in Science & Concept Explainer Engine
    # -------------------------------------------------------------------------
    def answer_science_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Answers fundamental scientific, physics, biology, and computational concepts."""
        q = query.lower().strip()

        # Why is the sky blue?
        if "sky blue" in q:
            return {
                "found": True,
                "text": (
                    "### Why is the Sky Blue?\n\n"
                    "The sky appears blue because of an optical phenomenon called **Rayleigh Scattering**:\n\n"
                    "1. **Sunlight Composition**: Sunlight reaches Earth's atmosphere as white light, composed of all colors of the rainbow (each with different wavelengths).\n"
                    "2. **Atmospheric Gas Interaction**: When sunlight strikes tiny nitrogen and oxygen molecules in our atmosphere, light with shorter wavelengths scatters much more strongly than longer wavelengths.\n"
                    "3. **Shorter Blue Wavelengths**: Blue and violet light have the shortest wavelengths, so they scatter in every direction across the sky.\n"
                    "4. **Human Eye Sensitivity**: While violet light scatters even more than blue, human eyes are significantly more sensitive to blue light, so we perceive the daytime sky as vibrant blue!"
                ),
                "source": "AI Science & Physics Engine",
                "badge": "PHYSICS / OPTICS",
                "category": "Science"
            }

        # Quantum Computing
        if "quantum computing" in q or "quantum computer" in q:
            return {
                "found": True,
                "text": (
                    "### What is Quantum Computing?\n\n"
                    "**Quantum Computing** leverages principles of quantum mechanics to process information at speeds exponentially faster than classical supercomputers for certain problem classes:\n\n"
                    "• **Bits vs. Qubits**: Classical computers encode data into binary bits ($0$ or $1$). Quantum computers use **quantum bits (qubits)**.\n"
                    "• **Superposition**: A qubit can exist in a linear combination of states $|0\\rangle$ and $|1\\rangle$ simultaneously, allowing parallel evaluation of billions of possibilities.\n"
                    "• **Entanglement**: Qubits can become intertwined such that the state of one instantly dictates the state of another, regardless of physical distance.\n"
                    "• **Applications**: Molecular simulation for drug discovery, optimizing logistics networks, material science, and high-security cryptography."
                ),
                "source": "AI Science & Physics Engine",
                "badge": "QUANTUM PHYSICS",
                "category": "Computer Science"
            }

        # Photosynthesis
        if "photosynthesis" in q:
            return {
                "found": True,
                "text": (
                    "### What is Photosynthesis?\n\n"
                    "**Photosynthesis** is the biological process by which green plants, algae, and cyanobacteria convert light energy into chemical energy stored in glucose.\n\n"
                    "#### The Chemical Equation:\n"
                    "$$6\\text{CO}_2 + 6\\text{H}_2\\text{O} + \\text{Light Energy} \\longrightarrow \\text{C}_6\\text{H}_{12}\\text{O}_6 + 6\\text{O}_2$$\n\n"
                    "#### Two Main Stages:\n"
                    "1. **Light-Dependent Reactions** (Thylakoid membranes): Chlorophyll absorbs photons, splits water molecules ($H_2O$), generates ATP & NADPH, and releases Oxygen ($O_2$).\n"
                    "2. **Calvin Cycle / Light-Independent** (Stroma): Uses ATP & NADPH to fix Carbon Dioxide ($CO_2$) into energy-rich glucose sugar molecules."
                ),
                "source": "AI Science & Physics Engine",
                "badge": "BIOLOGY / CHEMISTRY",
                "category": "Science"
            }

        # How airplanes fly
        if "airplanes fly" in q or "airplane fly" in q or "plane fly" in q:
            return {
                "found": True,
                "text": (
                    "### How Do Airplanes Fly? (The 4 Forces of Flight)\n\n"
                    "Airplanes stay aloft through the dynamic balance of **four fundamental aerodynamic forces**:\n\n"
                    "1. **Lift**: Generated by the wings (airfoils). Due to wing curvature (camber) and angle of attack, airflow travels faster over the top surface, creating lower pressure above and higher pressure below (**Bernoulli's Principle**), while deflecting air downward (**Newton's Third Law**).\n"
                    "2. **Weight (Gravity)**: The downward gravitational pull on the aircraft mass.\n"
                    "3. **Thrust**: The forward mechanical force produced by jet engines or propellers overcoming drag.\n"
                    "4. **Drag**: The aerodynamic resistance of the air against the moving plane.\n\n"
                    "*When Lift $\\ge$ Weight and Thrust $\\ge$ Drag, the aircraft ascends and cruises smoothly!*"
                ),
                "source": "AI Science & Physics Engine",
                "badge": "AERODYNAMICS",
                "category": "Physics"
            }

        # AI vs Machine Learning vs Deep Learning
        if ("machine learning" in q or "deep learning" in q or "artificial intelligence" in q) and ("difference" in q or "vs" in q or "what is" in q):
            return {
                "found": True,
                "text": (
                    "### Artificial Intelligence vs Machine Learning vs Deep Learning\n\n"
                    "Think of these three concepts as concentric circles:\n\n"
                    "1. **Artificial Intelligence (AI)** — *The Broadest Field*\n"
                    "   • Any computer system designed to simulate human cognitive functions (problem-solving, reasoning, planning, perception).\n"
                    "2. **Machine Learning (ML)** — *A Subset of AI*\n"
                    "   • Systems that automatically learn and improve from data experience without being explicitly programmed (e.g. TF-IDF vector space, linear regression, random forests).\n"
                    "3. **Deep Learning (DL)** — *A Subset of ML*\n"
                    "   • Uses multi-layered Artificial Neural Networks inspired by the human brain (e.g. Transformers, Large Language Models like GPT-4 and Gemini, Convolutional Vision Networks)."
                ),
                "source": "AI Science & Computing Engine",
                "badge": "AI ARCHITECTURE",
                "category": "Artificial Intelligence"
            }

        # Speed of Light
        if "speed of light" in q:
            return {
                "found": True,
                "text": (
                    "### The Speed of Light ($c$)\n\n"
                    "The speed of light in a vacuum is a universal physical constant:\n\n"
                    "• **Exact Metric Value**: **$299,792,458$ meters per second** (~$300,000$ km/s)\n"
                    "• **Imperial Value**: Approximately **$186,282$ miles per second**\n"
                    "• **Light travel time**: Sunlight takes approximately **$8$ minutes and $20$ seconds** to travel $150$ million kilometers to Earth.\n"
                    "• **Einstein's Relativity**: According to Einstein's Theory of Special Relativity ($E = mc^2$), $c$ represents the maximum speed limit at which conventional matter and information can travel in the universe."
                ),
                "source": "AI Science & Physics Engine",
                "badge": "ASTROPHYSICS",
                "category": "Physics"
            }

        # How the internet works
        if "how does the internet work" in q or "how internet works" in q:
            return {
                "found": True,
                "text": (
                    "### How Does the Internet Work?\n\n"
                    "The Internet is a global network of interconnected computers communicating via standardized protocols:\n\n"
                    "1. **URL Request**: When you type a web address (e.g. `example.com`), your browser contacts a **DNS (Domain Name System)** server to convert the domain into a numerical IP address (like `93.184.216.34`).\n"
                    "2. **TCP/IP Handshake**: Your device establishes a reliable connection with the destination server via TCP packets.\n"
                    "3. **Packet Routing**: Data is broken into small chunks called **packets**, routed across undersea fiber-optic cables and routers worldwide, and reassembled at destination.\n"
                    "4. **HTTPS / TLS Encryption**: Secure cryptographic protocols ensure your private data cannot be intercepted.\n"
                    "5. **Browser Rendering**: The server responds with HTML, CSS, and JavaScript, which your browser renders into an interactive website."
                ),
                "source": "AI Computer Science Engine",
                "badge": "NETWORKING",
                "category": "Technology"
            }

        return None

    # -------------------------------------------------------------------------
    # 4. Built-in Writing & Professional Productivity Assistant
    # -------------------------------------------------------------------------
    def answer_creative_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Generates professional letters, emails, productivity frameworks, and creative texts."""
        q = query.lower().strip()

        # Leave / Sick request email
        if "leave" in q and "email" in q or "sick day" in q or "time off" in q:
            return {
                "found": True,
                "text": (
                    "### Professional Leave Request Email Template\n\n"
                    "**Subject:** Leave Request - [Your Full Name] - [Start Date] to [End Date]\n\n"
                    "Dear [Manager's Name],\n\n"
                    "I am writing to formally request leave from [Start Date] through [End Date] due to [personal reasons / medical appointment / vacation]. I plan to return to work on [Return Date].\n\n"
                    "Prior to my departure, I will ensure all active priority tasks are up-to-date. During my absence, [Colleague's Name] has kindly agreed to cover urgent inquiries.\n\n"
                    "I will have limited access to email in case of an emergency. Thank you for your consideration and understanding.\n\n"
                    "Warm regards,\n\n"
                    "[Your Name]  \n"
                    "[Your Job Title]"
                ),
                "source": "AI Writing Assistant",
                "badge": "WRITING TEMPLATE",
                "category": "Productivity"
            }

        # Pomodoro Technique
        if "pomodoro" in q:
            return {
                "found": True,
                "text": (
                    "### The Pomodoro Productivity Framework\n\n"
                    "Developed by Francesco Cirillo, the **Pomodoro Technique** breaks deep work into structured intervals:\n\n"
                    "1. **Choose a Single Task**: Remove all distractions (turn off notifications).\n"
                    "2. **Set a 25-Minute Timer**: Focus with 100% intensity until the timer rings (one 'Pomodoro').\n"
                    "3. **Take a 5-Minute Break**: Stretch, drink water, or look away from screens.\n"
                    "4. **Repeat 4 Times**: After 4 cycles (100 mins of focused work), take a longer **15 to 30-minute restorative break**.\n\n"
                    "*Prevents burnout, maintains peak cognitive focus, and combats procrastination!*"
                ),
                "source": "AI Productivity Assistant",
                "badge": "PRODUCTIVITY",
                "category": "Productivity"
            }

        return None

    # -------------------------------------------------------------------------
    # 5. Safe Math Evaluator
    # -------------------------------------------------------------------------
    def answer_math(self, query: str) -> Optional[Dict[str, Any]]:
        """Detects and calculates mathematical expressions safely."""
        q = query.lower().strip()

        # Check percentage calculation: "what is 15% of 250" or "15% of 250"
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", q)
        if pct_match:
            pct = float(pct_match.group(1))
            val = float(pct_match.group(2))
            res = (pct / 100.0) * val
            return {
                "found": True,
                "text": f"{pct}% of {val:g} is **{res:g}**.",
                "source": "Safe Math Engine",
                "badge": "CALCULATION",
                "category": "Mathematics"
            }

        # Check compound interest inquiry
        if "compound interest" in q and ("formula" in q or "calculate" in q or "how" in q):
            return {
                "found": True,
                "text": (
                    "### Compound Interest Formula\n\n"
                    "$$A = P \\left(1 + \\frac{r}{n}\\right)^{nt}$$\n\n"
                    "Where:\n"
                    "• **$A$** = Final Accrued Amount (Principal + Interest)\n"
                    "• **$P$** = Principal Initial Balance\n"
                    "• **$r$** = Annual Interest Rate (as a decimal, e.g. 5% = 0.05)\n"
                    "• **$n$** = Compounding frequency per year ($n=12$ for monthly, $n=365$ for daily)\n"
                    "• **$t$** = Number of years\n\n"
                    "**Example**: $1,000 invested at 7% compounded monthly for 10 years grows to **$2,009.66**!"
                ),
                "source": "Math & Financial Engine",
                "badge": "FINANCIAL MATH",
                "category": "Mathematics"
            }

        # Standard arithmetic expressions
        clean_expr = re.sub(r"^(what\s+is|calculate|evaluate|solve)\s+", "", q).strip("? ")
        if re.match(r"^[\d\s\+\-\*\/\(\)\.\^%]+$", clean_expr) and any(op in clean_expr for op in "+-*/^%"):
            try:
                clean_expr = clean_expr.replace("^", "**")
                parsed = ast.parse(clean_expr, mode="eval")
                val = _safe_eval_math(parsed.body)
                fmt_val = f"{val:,.4f}".rstrip("0").rstrip(".") if isinstance(val, float) else f"{val:,}"
                return {
                    "found": True,
                    "text": f"The result of `{clean_expr.replace('**', '^')}` is **{fmt_val}**.",
                    "source": "Safe Math Engine",
                    "badge": "CALCULATION",
                    "category": "Mathematics"
                }
            except Exception:
                pass
        return None

    # -------------------------------------------------------------------------
    # 6. Real-Time Date & Time Service
    # -------------------------------------------------------------------------
    def answer_datetime(self, query: str) -> Optional[Dict[str, Any]]:
        """Answers real-time clock, calendar, and date inquiries."""
        q = query.lower().strip()
        time_triggers = ["what time is it", "current time", "what is the time", "tell me the time"]
        date_triggers = [
            "what is today's date", "what is the date", "what date is today",
            "what day is today", "today's date", "current date"
        ]

        now = datetime.datetime.now()

        if any(t in q for t in time_triggers):
            time_str = now.strftime("%I:%M %p")
            return {
                "found": True,
                "text": f"The current local system time is **{time_str}**.",
                "source": "System Clock",
                "badge": "TIME & DATE",
                "category": "Utility"
            }

        if any(t in q for t in date_triggers):
            date_str = now.strftime("%A, %B %d, %Y")
            return {
                "found": True,
                "text": f"Today is **{date_str}**.",
                "source": "System Clock",
                "badge": "TIME & DATE",
                "category": "Utility"
            }

        return None

    # -------------------------------------------------------------------------
    # 7. Conversational Chit-Chat & Personality System
    # -------------------------------------------------------------------------
    def answer_chitchat(self, query: str) -> Optional[Dict[str, Any]]:
        """Handles identity, capabilities, jokes, and greeting chit-chat."""
        q = query.lower().strip().rstrip("?!. ")

        # Identity & Capabilities
        if any(p == q or q.startswith(p) for p in IDENTITY_PROMPTS):
            return {
                "found": True,
                "text": (
                    "I am your **AI Supercharged Assistant**! 🤖✨\n\n"
                    "I combine the speed of **Gemini** and the conversational depth of **ChatGPT** with full enterprise e-commerce support:\n\n"
                    "• **Coding & Engineering**: Python, JavaScript, SQL, HTML/CSS, Git, algorithms, and regex.\n"
                    "• **Science & Philosophy**: Physics, quantum mechanics, biology, cosmology, and computing.\n"
                    "• **Productivity & Writing**: Professional emails, templates, frameworks, and explanations.\n"
                    "• **E-Commerce & Orders**: 60+ store FAQs covering live order tracking, shipping rates, refunds, 2FA security, loyalty perks, and 24/7 customer care.\n"
                    "• **Universal Web Search**: Instant real-time factual lookups via Wikipedia & Web Knowledge."
                ),
                "source": "AI Assistant Core",
                "badge": "AI ASSISTANT",
                "category": "Identity"
            }

        # Jokes
        if "joke" in q or "make me laugh" in q:
            return {
                "found": True,
                "text": random.choice(JOKES),
                "source": "AI Assistant Core",
                "badge": "HUMOR",
                "category": "Chit-Chat"
            }

        # Well-being / Mood
        if q in ("how are you", "how are you doing", "how do you feel", "how's it going"):
            return {
                "found": True,
                "text": "I'm functioning with 100% neural accuracy and ready to solve any question you have! What can we explore or build together today?",
                "source": "AI Assistant Core",
                "badge": "CHIT-CHAT",
                "category": "Chit-Chat"
            }

        return None

    # -------------------------------------------------------------------------
    # 8. Wikipedia Two-Phase Search & Summary Engine
    # -------------------------------------------------------------------------
    def clean_query_subject(self, query: str) -> str:
        """Extracts the core entity or concept from conversational user phrasing."""
        clean = query.lower().strip().rstrip("?!. ")

        prefixes = [
            r"^(do you know\s+(where|what|who|how|why)\s+(is|are|was|were)?\s*)",
            r"^(can you tell me\s+(where|what|who|how|about)?\s*(is|are)?\s*)",
            r"^(tell me\s+(where|what|who|about)?\s*(is|are)?\s*)",
            r"^(where is\s+(the\s+)?)",
            r"^(where are\s+(the\s+)?)",
            r"^(what is\s+(a\s+|an\s+|the\s+)?)",
            r"^(what are\s+(the\s+)?)",
            r"^(who is\s+(the\s+)?)",
            r"^(who was\s+(the\s+)?)",
            r"^(who were\s+(the\s+)?)",
            r"^(what does\s+)",
            r"^(explain\s+(to me\s+)?(what\s+is\s+|how\s+)?)",
            r"^(define\s+)",
            r"^(meaning of\s+)",
            r"^(history of\s+)",
            r"^(information about\s+)"
        ]
        for p in prefixes:
            clean = re.sub(p, "", clean, flags=re.IGNORECASE).strip()

        # Remove trailing words like " is", " are", " located", " situated", " in simple terms", " mean"
        clean = re.sub(r"\s+(is|are|located|situated|mean|in simple terms)$", "", clean, flags=re.IGNORECASE).strip()
        return clean

    def query_wikipedia(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Two-phase Wikipedia search:
        Phase 1: OpenSearch or Full-Text search to resolve canonical title and snippet
        Phase 2: REST page summary for clean, authoritative encyclopedia response
        """
        clean = self.clean_query_subject(query)
        if not clean or len(clean) < 2:
            return None

        canonical_title = None

        # 1. Try direct REST page summary first if title is capitalized or known
        try:
            summary_url = (
                "https://en.wikipedia.org/api/rest_v1/page/summary/"
                + urllib.parse.quote(clean.title().replace(" ", "_"))
            )
            req = urllib.request.Request(summary_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                extract = data.get("extract", "").strip()
                title = data.get("title", clean.title())
                page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

                if extract and len(extract) > 40:
                    formatted_text = f"### {title}\n\n{extract}"
                    if page_url:
                        formatted_text += f"\n\n🔗 *Source: [Wikipedia — {title}]({page_url})*"

                    return {
                        "found": True,
                        "text": formatted_text,
                        "title": title,
                        "url": page_url,
                        "source": "Wikipedia Universal Knowledge",
                        "badge": "ENCYCLOPEDIA",
                        "category": "General Knowledge"
                    }
        except Exception:
            pass

        # 2. Try OpenSearch to find canonical title
        try:
            search_url = (
                "https://en.wikipedia.org/w/api.php?action=opensearch&search="
                + urllib.parse.quote(clean)
                + "&limit=2&namespace=0&format=json"
            )
            req = urllib.request.Request(search_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if len(data) > 1 and data[1]:
                    canonical_title = data[1][0]
        except Exception:
            pass

        # 3. Try Full-Text Search if OpenSearch yielded nothing
        if not canonical_title:
            try:
                ft_url = (
                    "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch="
                    + urllib.parse.quote(clean)
                    + "&srlimit=1&format=json"
                )
                req = urllib.request.Request(ft_url, headers={"User-Agent": self.user_agent})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("query", {}).get("search", [])
                    if results:
                        canonical_title = results[0].get("title")
            except Exception:
                pass

        target_title = canonical_title if canonical_title else clean.replace(" ", "_")

        # 4. Fetch Page Summary for resolved title
        try:
            summary_url = (
                "https://en.wikipedia.org/api/rest_v1/page/summary/"
                + urllib.parse.quote(target_title.replace(" ", "_"))
            )
            req = urllib.request.Request(summary_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                extract = data.get("extract", "").strip()
                title = data.get("title", clean.title())
                page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

                if extract and len(extract) > 40:
                    formatted_text = f"### {title}\n\n{extract}"
                    if page_url:
                        formatted_text += f"\n\n🔗 *Source: [Wikipedia — {title}]({page_url})*"

                    return {
                        "found": True,
                        "text": formatted_text,
                        "title": title,
                        "url": page_url,
                        "source": "Wikipedia Universal Knowledge",
                        "badge": "ENCYCLOPEDIA",
                        "category": "General Knowledge"
                    }
        except Exception:
            pass

        return None

    # -------------------------------------------------------------------------
    # 9. DuckDuckGo Instant Answer
    # -------------------------------------------------------------------------
    def query_duckduckgo(self, query: str) -> Optional[Dict[str, Any]]:
        """Queries DuckDuckGo Instant Answer API for quick definitions and facts."""
        clean = query.strip("?!. ")
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean)}&format=json&no_html=1"
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                abstract = data.get("AbstractText", "").strip()
                heading = data.get("Heading", clean)
                source_url = data.get("AbstractURL", "")

                if abstract and len(abstract) > 30:
                    text = f"### {heading}\n\n{abstract}"
                    if source_url:
                        text += f"\n\n🔗 *Source: [{data.get('AbstractSource', 'Web Knowledge')}]({source_url})*"
                    return {
                        "found": True,
                        "text": text,
                        "title": heading,
                        "url": source_url,
                        "source": "Web Knowledge Engine",
                        "badge": "FACT CHECK",
                        "category": "General Knowledge"
                    }
        except Exception:
            pass
        return None

    # -------------------------------------------------------------------------
    # Master Answer Function
    # -------------------------------------------------------------------------
    def answer(self, query: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Master resolver for ANY general, technical, scientific, or creative inquiry.
        Orchestration order:
        1. Safe Math / Arithmetic
        2. Real-time Date / Time
        3. Conversational Chit-Chat / Identity
        4. Google Gemini Generative AI (if user key or env key configured)
        5. Built-in Technical & Coding Knowledge Base
        6. Built-in Science & Concept Explainer Base
        7. Built-in Writing & Productivity Assistant
        8. Two-phase Wikipedia Full-Text Search
        9. DuckDuckGo Instant Answers
        """
        # 1. Math calculation
        math_ans = self.answer_math(query)
        if math_ans:
            return math_ans

        # 2. Time & Date
        dt_ans = self.answer_datetime(query)
        if dt_ans:
            return dt_ans

        # 3. Chit-Chat / Personality
        chat_ans = self.answer_chitchat(query)
        if chat_ans:
            return chat_ans

        # 4. Google Gemini Generative AI Gateway
        gem_ans = self.query_gemini(query, api_key=api_key)
        if gem_ans:
            return gem_ans

        # 5. Technical & Coding Knowledge
        tech_ans = self.answer_technical_query(query)
        if tech_ans:
            return tech_ans

        # 6. Science & Concepts
        sci_ans = self.answer_science_query(query)
        if sci_ans:
            return sci_ans

        # 7. Creative & Productivity
        creative_ans = self.answer_creative_query(query)
        if creative_ans:
            return creative_ans

        # 8. Wikipedia Encyclopedia Full-Text Search
        wiki_ans = self.query_wikipedia(query)
        if wiki_ans:
            return wiki_ans

        # 9. DuckDuckGo Web Knowledge
        ddg_ans = self.query_duckduckgo(query)
        if ddg_ans:
            return ddg_ans

        return None
