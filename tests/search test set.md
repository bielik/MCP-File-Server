# Search Test Suite for MCP KnowledgeExplorer

## FILE_SEARCH Tests

### Test ID: FILE_001
**Query:** Find file or folder with "react" in its name
**Type:** File search (name pattern)
**Expected Results:**
- **Folders:**
  - `C:\Users\MartinBielik\MCP Test\materials\05_Developing Front-End Apps with React`
  - `C:\Users\MartinBielik\MCP Test\Working with react`
- **Files:**
  - `002_video_Introduction to Front-End Frameworks and React . Duration_ 5 minutes 5 min.md`
  - `002_video_Introduction to Front-End Frameworks and React . Duration_ 5 minutes 5 min.mp4`
  - `003_video_Understand React Structure . Duration_ 5 minutes 5 min.md`
  - `003_video_Understand React Structure . Duration_ 5 minutes 5 min.mp4`
  - `React is complicated.txt`
**Edge Case:** Case insensitive matching

### Test ID: FILE_002
**Query:** Find file or folder from September 22nd with "react" in its name
**Type:** File search (name pattern + date filter)
**Expected Results:**
- **Folders:**
  - `C:\Users\MartinBielik\MCP Test\Working with react` (created 2024-09-22)
- **Files:**
  - `React is complicated.txt` (modified 2024-09-22)
**Edge Case:** Date-based filtering combined with name search

### Test ID: FILE_003
**Query:** Find .md files
**Type:** File search (extension filter)
**Expected Results:**
- **Files:**
  - `002_video_Introduction to Front-End Frameworks and React . Duration_ 5 minutes 5 min.md`
  - `003_video_Understand React Structure . Duration_ 5 minutes 5 min.md`
  - All other .md files in the test dataset
**Edge Case:** Extension-based filtering

### Test ID: FILE_004
**Query:** Find file with "react" in its name and size over 1MB
**Type:** File search (name pattern + size filter)
**Expected Results:**
- **Files:**
  - `002_video_Introduction to Front-End Frameworks and React . Duration_ 5 minutes 5 min.mp4` (>1MB)
  - `003_video_Understand React Structure . Duration_ 5 minutes 5 min.mp4` (>1MB)
**Edge Case:** Size-based filtering combined with name search

## KEYWORD_SEARCH Tests

### Test ID: KEYWORD_001
**Query:** "Fahrvergnügen"
**Type:** Keyword search (German compound word)
**Expected Results:**
- **Primary match:** `Fahrvergnügen_driving_pleasure.txt`
- **Secondary match:** Any file discussing "driving pleasure" or automotive joy
**Edge Case:** German compound word recognition

### Test ID: KEYWORD_002
**Query:** "developement" (typo)
**Type:** Keyword search (misspelling tolerance)
**Expected Results:**
- **Primary match:** `web_developement_guide.txt` (exact typo match)
- **Secondary match:** Any file with "development" (typo correction)
**Edge Case:** Common typo tolerance

### Test ID: KEYWORD_003
**Query:** "javascript"
**Type:** Keyword search (case insensitive)
**Expected Results:**
- **Primary matches:**
  - `JavaScript_vs_javascript.md`
  - Any file with "JavaScript", "JAVASCRIPT", "Javascript" variations
**Edge Case:** Case sensitivity handling

### Test ID: KEYWORD_004
**Query:** "node.js"
**Type:** Keyword search (special characters)
**Expected Results:**
- **Primary match:** `node.js_tutorial.txt`
- **Secondary match:** Any file discussing Node.js development
**Edge Case:** Punctuation in search terms

### Test ID: KEYWORD_005
**Query:** "recieve" (typo)
**Type:** Keyword search (common misspelling)
**Expected Results:**
- **Primary match:** `recieve_data_methods.md` (exact typo match)
- **Secondary match:** Any file with "receive" (corrected spelling)
**Edge Case:** Common misspelling correction

### Test ID: KEYWORD_006
**Query:** "Zeitgeist"
**Type:** Keyword search (German word in mixed content)
**Expected Results:**
- **Primary match:** `Zeitgeist_and_culture.md`
- **Secondary match:** Any file discussing cultural trends or spirit of the times
**Edge Case:** German loanwords in English text

### Test ID: KEYWORD_007
**Query:** "C++"
**Type:** Keyword search (special characters in programming)
**Expected Results:**
- **Primary match:** `C++_programming.md`
- **Secondary match:** Any file discussing C++ development
**Edge Case:** Plus signs and programming language names

### Test ID: KEYWORD_008
**Query:** "seperate" (typo)
**Type:** Keyword search (separation concept)
**Expected Results:**
- **Primary match:** `seperate_concerns.txt` (exact typo match)
- **Secondary match:** Any file with "separate" (corrected spelling)
**Edge Case:** Another common typo

### Test ID: KEYWORD_009
**Query:** "Donaudampfschifffahrt"
**Type:** Keyword search (very long German compound)
**Expected Results:**
- **Primary match:** `Donaudampfschifffahrt_navigation.txt`
- **Secondary match:** Any file about Danube river navigation or steamships
**Edge Case:** Very long German compound word decomposition

### Test ID: KEYWORD_010
**Query:** "API"
**Type:** Keyword search (acronym)
**Expected Results:**
- **Primary match:** `API_Documentation.md`
- **Secondary match:** Any file discussing Application Programming Interfaces
**Edge Case:** Acronym handling and capitalization

## SEMANTIC_SEARCH Tests

### Test ID: SEMANTIC_001
**Query:** "machine learning without neural networks"
**Type:** Semantic search (concept exclusion)
**Expected Results:**
- **Primary match:** `machine_learning_basics.md` (discusses supervised learning, statistical models)
- **Avoid:** `deep_learning_concepts.md` (focuses on neural networks)
**Edge Case:** Semantic understanding with exclusion criteria

### Test ID: SEMANTIC_002
**Query:** "authentication and user security"
**Type:** Semantic search (security concepts)
**Expected Results:**
- **Primary match:** `authentication_security.md`
- **Secondary match:** Any file discussing login, passwords, OAuth, JWT
**Edge Case:** Broad security concept matching

### Test ID: SEMANTIC_003
**Query:** "statistical hypothesis testing"
**Type:** Semantic search (statistical concepts)
**Expected Results:**
- **Primary matches:**
  - `statistical_inference.txt`
  - `data_validation.md` (discusses null hypothesis testing)
- **Secondary match:** Any file with p-values, confidence intervals
**Edge Case:** Cross-file semantic connections

### Test ID: SEMANTIC_004
**Query:** "container technology without mentioning Docker"
**Type:** Semantic search (concept without brand names)
**Expected Results:**
- **Primary match:** `virtualization_explained.md` (discusses containers vs VMs)
- **Secondary match:** `containerization_guide.txt` (Docker implementation)
**Edge Case:** Generic concept vs specific implementation

### Test ID: SEMANTIC_005
**Query:** "visual design and styling"
**Type:** Semantic search (design concepts)
**Expected Results:**
- **Primary matches:**
  - `web_styling_guide.md` (visual design principles)
  - `css_best_practices.txt` (CSS implementation)
**Edge Case:** Concept to implementation mapping

### Test ID: SEMANTIC_006
**Query:** "distributed system communication"
**Type:** Semantic search (architecture patterns)
**Expected Results:**
- **Primary match:** `microservices_architecture.md`
- **Secondary match:** Any file discussing service communication, APIs, messaging
**Edge Case:** Architectural pattern understanding

### Test ID: SEMANTIC_007
**Query:** "training AI models"
**Type:** Semantic search (AI/ML concepts)
**Expected Results:**
- **Primary matches:**
  - `deep_learning_concepts.md` (backpropagation, training strategies)
  - `machine_learning_basics.md` (model training concepts)
**Edge Case:** Multiple files with related but different AI concepts

### Test ID: SEMANTIC_008
**Query:** "data quality and validation"
**Type:** Semantic search (data science concepts)
**Expected Results:**
- **Primary match:** `data_validation.md`
- **Secondary match:** `statistical_inference.txt` (related statistical concepts)
**Edge Case:** Related data science concepts across files

### Test ID: SEMANTIC_009
**Query:** "deployment automation"
**Type:** Semantic search (DevOps concepts)
**Expected Results:**
- **Primary match:** `containerization_guide.txt` (CI/CD pipelines)
- **Secondary match:** Any file discussing automation, deployment strategies
**Edge Case:** DevOps concept understanding

### Test ID: SEMANTIC_010
**Query:** "responsive web layouts"
**Type:** Semantic search (web development)
**Expected Results:**
- **Primary matches:**
  - `web_styling_guide.md` (responsive layouts)
  - `css_best_practices.txt` (Flexbox and Grid)
**Edge Case:** Web development technique mapping