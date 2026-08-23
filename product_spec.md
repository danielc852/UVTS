# UVTS Product Specification

**Product name:** UVTS (User-View Testing Stimulation)  
**Version:** First release  
**Audience:** Non-technical writers, product owners, designers, and development teams  
**Last updated:** 2026-08-23  

## 1. What is UVTS?

UVTS helps a writer check whether a product or software manual contains the information needed for questions that real users may ask.

The writer uploads a PDF manual and chooses the kinds of questions to test. UVTS creates sample user questions, checks whether the needed information exists in the manual, and produces a report. The report shows what information is present, incomplete, or missing.

The first version of UVTS supports:

- One PDF manual at a time
- A manual of up to 20 pages
- Up to 15 questions in one test
- Three main question types
- A basic results report with recommendations and follow-up questions

## 2. Why is this product needed?

Writers usually review a manual by checking whether all planned sections have been written. Users approach a manual differently. They ask questions based on what they want to do, what they already know, and what has gone wrong.

For example, a manual may explain how to turn on automatic backup and explain export formats in another section. It may not clearly answer this user question:

> Can I change the export format after automatic backup has already been turned on?

UVTS helps writers find these gaps before users need to contact support.

## 3. Main Goal

UVTS should help a writer answer one main question:

> Does this manual give different kinds of users enough information to complete their tasks and solve likely problems?

The report should be easy to understand without technical or AI knowledge.

## 4. Who will use UVTS?

The main user is a person who writes or reviews product information but may not have a technical background.

Examples include:

- A content writer preparing a product manual
- A product owner checking whether a manual is ready to publish
- A customer support manager reviewing common user problems
- A quality reviewer checking whether important information is covered

## 5. Typical User Journey

The complete journey stays on one page:

1. The writer uploads a PDF manual and UVTS checks that it can be used.
2. The writer generates questions using the suggested setup or adjusts the question settings.
3. The writer reviews the complete question list.
4. The writer starts the evaluation and watches its progress.
5. UVTS reveals the report with results and suggested improvements below the evaluation.

## 6. Core Features

### 6.1 Document Box

The Document Box is where the writer uploads the manual.

#### What the writer can do

- Upload one PDF file.
- See the file name and number of pages.
- Remove the file or replace it before starting a test.
- See whether the file is being uploaded, checked, processed, or is ready.

#### File rules

- The file must be a PDF.
- The PDF must contain between 1 and 20 pages.
- The PDF must not be password-protected.
- The PDF must contain readable text.
- Scanned pages that contain only images are not supported in the first version.
- Only one manual can be tested at a time.

#### What happens when there is a problem

UVTS must explain the problem in plain language and tell the writer what to do next.

Examples:

- “Upload a PDF file.”
- “This PDF has 24 pages. UVTS currently supports up to 20 pages.”
- “This PDF is password-protected. Remove the password and upload it again.”
- “UVTS could not read the text in this PDF. Scanned documents are not supported yet.”

#### The feature is complete when

- A suitable PDF can be uploaded and reaches a Ready state.
- A file with more than 20 pages is rejected with a clear message.
- The writer cannot continue until the manual is ready.
- UVTS remembers the page number of each piece of text so it can show evidence later.
- Replacing the manual removes questions and results from the old manual.

### 6.2 Test Configuration

Test Configuration lets the writer decide which questions UVTS should create.

The setup separates three ideas:

- **Question type:** how the question should use the manual
- **Topic:** what the question is about
- **User viewpoint:** the kind of person asking the question

#### Question types

The first version includes three types:

1. **Basic question**
   - Looks for a direct fact or a short set of steps.
   - The answer will normally be found in one part of the manual.
   - Example: “How do I reset my password?”
2. **Cross-paragraph question**
   - Needs information from two or more paragraphs, sections, or pages.
   - Example: “Can I change the export format after turning on automatic backup?”
3. **Edge-case question**
   - Asks about an unusual situation, a limit, a failed step, or an exception.
   - Example: “What should I do if setup stops before my device appears?”

#### Topics

The writer can choose one or more topics that are relevant to the manual:

- Setup and requirements
- Main product tasks
- Settings and customization
- Troubleshooting and recovery
- Limits and unusual situations
- Safety, privacy, and data handling

If a topic does not appear to be relevant, UVTS can make it unavailable and explain why.

#### User viewpoints

The writer can choose one or more viewpoints:

- **Beginner:** does not know the product or its special terms
- **Regular user:** knows the common tasks but may need help with a problem
- **Advanced user:** asks about settings, limits, and less common situations

These viewpoints describe the sample users asking the questions. They are not UVTS account types.

#### Number of questions

- The writer can choose between 1 and 15 questions.
- At least one question type, one topic, and one user viewpoint must be selected.
- The writer can choose how many questions of each type to create.
- The numbers for all question types must add up to the total.
- If the writer does not choose a split, UVTS divides the questions as evenly as possible.

The suggested starting setup is:

- 9 questions in total
- 3 Basic questions
- 3 Cross-paragraph questions
- 3 Edge-case questions
- All relevant topics
- Beginner, Regular user, and Advanced user viewpoints

#### The feature is complete when

- The writer cannot request fewer than 1 or more than 15 questions.
- The writer cannot continue when a required choice is missing.
- A clear summary shows what questions will be created.
- UVTS saves the choices used for each test.

### 6.3 User-Question Generation

UVTS creates realistic questions based on the manual and the writer's choices.

The UVTS AI agent uses Qwen3.8 27B through OpenRouter to create the question set.

#### Rules for good questions

Each question must:

- Sound like something a real user might ask.
- Have one question type, one topic, and one user viewpoint.
- Stay connected to the product and situations described in the manual.
- Be different from the other questions in the same set.
- Avoid mentioning page numbers or saying “according to the manual.”
- Use clear, natural language.

Basic questions should focus on common needs. Cross-paragraph questions should bring together related information from different parts of the manual. Edge-case questions may ask about reasonable problems that the manual does not fully explain. This is important because the purpose of UVTS is to find missing information, not only to repeat what is already written.

#### Reviewing the questions

Before testing, the writer can:

- Read the complete numbered question list.
- See the type, topic, and viewpoint for every question.
- Replace the whole set by selecting Generate Again.
- Start the test when satisfied with the set.

Generating again replaces the current questions, so UVTS must show a warning first. Questions cannot change after the test starts. This keeps the results connected to the exact questions that were tested.

Editing one question at a time is not included in the first version.

#### The feature is complete when

- UVTS creates the requested number of questions.
- The number of each question type matches the writer's setup.
- Every question shows its type, topic, and viewpoint.
- The set does not contain repeated questions.
- The question set is saved when testing begins.

### 6.4 Automated Testing

UVTS checks whether the manual contains the information needed for each generated question. It does not test whether an AI agent can write a correct answer.

The UVTS AI agent uses Qwen3.8 27B through OpenRouter to perform this information-presence check.

#### How the test works

For each question, UVTS:

1. Lists the main pieces of information the question requires.
2. Searches the manual for each piece of information.
3. Records which information is present, partly present, or missing.
4. Shows the pages where supporting information was found.
5. Gives the question an information-coverage status.

UVTS does not generate an answer to the question. It must not use outside knowledge or an AI agent's own knowledge to fill a gap. If the information is not in the manual, the result must say so.

#### Result status

Each question receives one of three results:

- **Information found:** The manual contains all important information needed for the question.
- **Information partly found:** The manual contains some relevant information, but an important step, condition, or detail is missing or unclear.
- **Information not found:** The manual does not contain relevant information for the question.

These results only show whether the information exists in the manual. They do not judge whether the information is factually correct, clearly written, or safe.

#### Evidence

For an Information found or Information partly found result, UVTS must show:

- The page number where the information was found
- A short text extract or a simple note describing the evidence
- More than one page when the needed information appears in different parts of the manual

If no useful information is found, UVTS must show “No supporting information found.” It must never create a false page reference.

#### Test summary numbers

UVTS shows:

- The main result as a clear sentence: **X questions are covered out of Y total questions.** For example: **7 questions are covered out of 10 total questions.**
- The number of questions where information was partly found
- The number of questions where information was not found
- Results grouped by question type
- Results grouped by topic
- Results grouped by user viewpoint

Only questions marked Information found count toward X. The total is the number of generated questions in the test. The found, partly found, not found, and failed counts must add up to that total.

#### Progress and failure

- The writer sees how many questions have been completed.
- If one question fails to process, UVTS continues with the others.
- Completed results are kept.
- The writer can try failed questions again.
- UVTS clearly marks a report that contains unfinished or failed questions.

#### The feature is complete when

- Every completed question has one information-coverage result.
- Every found or partly found result includes at least one real page reference.
- An Information not found result does not contain invented evidence.
- The summary numbers match the individual results.
- One failed question does not remove the other results.

### 6.5 Basic Report

The Basic Report explains the results and helps the writer decide what to improve.

The UVTS AI agent uses Qwen3.8 27B through OpenRouter to group information gaps and suggest manual improvements and follow-up questions.

#### Report contents

The report includes:

1. **Test summary**
   - Manual name and number of pages
   - Test date
   - Number of questions
   - Choices used to create the questions
   - Main result shown as **X questions are covered out of Y total questions.**
   - Counts for Information partly found and Information not found
2. **Coverage overview**
   - Results by question type
   - Results by topic
   - Results by user viewpoint
3. **Question results**
   - The question and its labels
   - Information found, partly found, or not found
   - Information found and information missing
   - Page references
4. **Main gaps**
   - Missing or incomplete information grouped by subject
   - The questions affected by each gap
   - An explanation of why the gap matters
5. **Recommendations**
   - Clear writing changes, such as adding a missing requirement, explaining a term, joining related steps, describing a limit, or adding recovery instructions
6. **Follow-up**
   - Suggested questions to use after the manual is updated
   - A suggestion to run the test again
   - Any failed questions that still need to be tested

#### Recommendation priority

- **High:** Missing information may stop a common task or may affect safety, privacy, or important data.
- **Medium:** Incomplete or scattered information may cause mistakes or support requests.
- **Low:** The information exists but could be easier to find or understand.

Every recommendation must connect to at least one test result. UVTS should recommend improvements to the manual, not changes to the product itself.

#### Report actions

The writer can:

- Read the full report in UVTS.
- Open a result to see its explanation and page evidence.
- Start another test with the same manual and different choices.
- Run the same type of test after updating the manual.

Downloading the report as a PDF or spreadsheet is not part of the first version.

#### The feature is complete when

- The report summary matches the detailed question results.
- The main result uses the sentence **X questions are covered out of Y total questions.**
- The report does not include AI-generated answers to the questions.
- Each main gap links to the questions it affects.
- Each recommendation links to a gap or question.
- Failed or unfinished tests are clearly marked.
- The language is understandable without technical knowledge.

### 6.6 AI Agent and Model Use

UVTS uses one internal AI agent to support question generation, testing, and report recommendations. This agent is part of the UVTS service; it is not a chatbot shown to the writer.

#### Selected service and model

- **AI service:** OpenRouter
- **Model:** Qwen3.8 27B
- **OpenRouter model ID:** `qwen/qwen3.8-27b`
- **Official model reference:** [Qwen3.8 27B on OpenRouter](https://openrouter.ai/qwen/qwen3.8-27b)

#### What the agent can do

- Read the text extracted from the uploaded manual.
- Generate questions using the selected types, topics, viewpoints, and counts.
- Identify the pieces of information needed for each question.
- Check whether those pieces of information exist in the manual.
- Connect found information to the correct manual pages.
- Group missing information and suggest improvements and follow-up questions.

#### What the agent must not do

- Generate or display an answer to a test question.
- Use its own knowledge or internet information to fill a gap in the manual.
- Mark information as found without supporting text and a real page reference.
- Change the generated questions after a test starts.
- Present its judgment as proof that the manual is factually correct or safe.

#### Service rules

- All model requests must go through the UVTS server. The OpenRouter access key must never be included in the browser or shown to the writer.
- Each test must record the service, model ID, and model settings used so the result can be reviewed later.
- UVTS must check that the model's output follows the required result format before showing it in the report.
- If OpenRouter or the selected model is unavailable, UVTS should keep the document and test settings and offer Retry.
- UVTS must not silently replace Qwen3.8 27B with another model. Any future model change must be recorded and tested before release.
- Manual content sent to the model must follow the privacy and retention rules in Section 10.

#### The feature is complete when

- Question generation, information checking, and recommendations use `qwen/qwen3.8-27b` through OpenRouter.
- The OpenRouter access key is only available on the UVTS server.
- Every successful information-presence result follows the three agreed statuses and evidence rules.
- No test result contains an AI-generated answer to the question.
- A model or service failure shows a clear Retry option without losing the writer's work.

## 7. Technical Direction and Stack Choice

This section records the first-release application stack and why it fits UVTS. It is intended to prevent the project from adopting framework features that the product does not need. Dependency versions must be pinned in the implementation lockfiles rather than in this product specification.

### 7.1 Selected application stack

#### Browser application

- **Build tool:** Vite
- **Interface framework:** React with TypeScript
- **Component system:** Astryx, following `uiux.md`
- **Application style:** Client-rendered single-page application
- **Server communication:** A typed HTTP API generated from or checked against the FastAPI OpenAPI contract

The browser application owns the five-stage workspace, form interaction, progress display, accessibility behavior, and report presentation. It must not contain the OpenRouter key, process PDFs, or make direct model requests.

#### Server application

- **API framework:** FastAPI
- **Data and model-output validation:** Pydantic
- **Language:** Python
- **PDF processing:** Python PDF libraries that preserve page provenance
- **AI access:** Server-side OpenRouter client

The server owns PDF validation and extraction, saved workflow state, question generation, evaluation, evidence verification, report data, retries, and deletion. Long-running evaluation must not depend on the lifetime of one HTTP request.

The exact database, durable-job system, and deployment platform remain implementation decisions. Whatever is selected must preserve work across a browser reload and must not lose completed question results when another question fails.

### 7.2 Why Vite and React fit UVTS

UVTS is an interactive workspace rather than a public content website. The first release does not need search-engine indexing, server-rendered pages, React Server Components, or static generation. Its main interface stays on one page and changes in response to uploads, configuration, background progress, retries, and expandable evidence.

Vite and React are selected because:

- React fits the stateful, component-based workflow and is required by the selected Astryx component system.
- Vite provides a focused development server and production build without introducing a second application server.
- The production browser application can be deployed as static files and can communicate with the Python API over HTTP.
- Vite supports TypeScript and React Fast Refresh, which keeps interface development quick.
- Separating the browser application from the API keeps PDF processing, AI calls, credentials, and evidence validation on the server.

This choice has costs:

- Vite is a build tool rather than a complete application framework. The project must explicitly choose routing, API-state handling, form handling, error boundaries, and testing conventions.
- Client-side routes such as `/tests/{testId}` require static-host fallback configuration so a direct browser reload returns the React application.
- Vite transpiles TypeScript but does not perform full type checking, so the build and continuous-integration checks must run the TypeScript compiler separately.
- The browser and API are separate applications, so API contract drift, cross-origin rules, local development, and deployment must be handled deliberately.

Official references: [Vite guide](https://vite.dev/guide/), [Vite features](https://vite.dev/guide/features), and [React guidance for starting from a build tool](https://react.dev/learn/build-a-react-app-from-scratch).

### 7.3 Why FastAPI is selected instead of Django

FastAPI is selected because UVTS needs a focused JSON API for a separate React application. Its Python type annotations, Pydantic validation, JSON Schema support, and generated OpenAPI description fit the product's strict request, response, and AI-output formats. Python also has mature PDF-processing libraries and is a natural place to implement the OpenRouter workflow.

Django remains a good framework, but its largest benefits are not yet central to the first release. UVTS currently has no decided account system, administration interface, content-management interface, or server-rendered form workflow. Using Django only as an API behind React would add its full application structure while still requiring a separate React application and an API layer.

FastAPI also has costs that the implementation must address:

- It does not choose the database, object-relational mapper, migrations, durable job runner, or administration interface.
- Long-running PDF and AI work must use a durable worker design; in-process request background tasks are not sufficient for work that must survive restarts.
- Authentication, permissions, retention, and operational tools will require explicit design if they enter the product scope.

Django should be reconsidered if accounts, permissions, an internal administration interface, database-heavy workflows, or server-rendered screens become major product requirements. Django with HTMX would also be a reasonable lower-JavaScript alternative if Astryx and the React interface were no longer requirements.

Official references: [FastAPI features](https://fastapi.tiangolo.com/features/) and [Django overview](https://docs.djangoproject.com/en/6.0/intro/overview/).

### 7.4 Why Vite is selected instead of Next.js

Next.js is useful when a React product needs server-side rendering, static generation, public search visibility, React Server Components, or a JavaScript full-stack server. UVTS already requires a Python server for PDF and AI processing, and its first-release workspace does not benefit materially from those rendering features.

Using Next.js with FastAPI would create both a Node.js application server and a Python application server. Vite avoids that additional runtime and keeps the boundary simple: React in the browser and FastAPI on the server.

Next.js should be reconsidered if UVTS later adds public report pages, content pages that need search visibility, server-rendered first loads, or a decision to move the backend into TypeScript.

### 7.5 Stack comparison

| Option | Strength for UVTS | Main drawback | First-release decision |
| --- | --- | --- | --- |
| Vite + React + FastAPI | Focused interactive UI, Astryx compatibility, strong Python PDF and AI support | Requires a clearly managed browser/API boundary | **Selected** |
| Next.js + FastAPI | Adds server rendering and a full React framework | Adds a Node server without a current product need | Not selected |
| React + Django API | Strong ORM, migrations, authentication, and administration | Many built-in features are not yet required; still needs a separate React application | Reconsider if accounts and administration become central |
| Django templates + HTMX | One main application stack and less browser JavaScript | Does not fit the selected Astryx React system and provides a different interaction model | Valid only if the React/Astryx direction changes |

### 7.6 Stack rules for the first release

- Use Astryx as the React component and accessibility source of truth. Do not introduce a competing general-purpose component system without a documented reason.
- Keep all PDF contents, AI prompts, AI calls, evidence validation, and secret values on the FastAPI side.
- Derive or verify browser API types against FastAPI's OpenAPI contract rather than maintaining unrelated duplicate definitions.
- Treat background evaluation as durable work. Closing or reloading the browser must not cancel it.
- Do not add server rendering, a Node.js production server, an administration system, or an account framework until a product requirement needs it.
- Revisit this decision if the assumptions in Sections 7.2–7.4 change.

## 8. Main Page

UVTS uses one vertically ordered workspace instead of separate workflow screens. It contains five sections:

1. **Upload manual:** The writer uploads one manual and sees when it is ready.
2. **Generate questions:** The writer uses the suggested setup or opens the question settings, then selects Generate questions.
3. **Review questions:** The writer reviews the generated list, generates a new set, or selects Evaluate questions.
4. **Evaluation:** The writer sees how many questions have been checked and whether any question needs to be tried again.
5. **Report:** The writer sees the overall results, individual questions, missing information, recommendations, and follow-up work.

Completed sections remain visible above the current section in a compact state. Future sections stay visible as locked placeholders that explain what must happen first. When a stage completes, the next section opens below it; UVTS does not navigate to another workflow page. Reloading the page restores the current test and stage.

## 9. Important Product Rules

1. One test uses one PDF manual.
2. The manual can contain no more than 20 pages.
3. One test can contain no more than 15 questions.
4. Every question has a type, topic, and user viewpoint.
5. Questions do not change after testing starts.
6. The uploaded manual is the only source used to check whether information exists.
7. Any result that says information was found must show a page reference.
8. Results measure whether information exists, not its accuracy or writing quality.
9. Every recommendation must be supported by a test result.
10. Replacing or deleting a manual also removes its unfinished questions and connected results.

## 10. Privacy, Safety, and Ease of Use

- Manuals and reports must be kept private.
- Files and results must be protected while stored and transferred.
- Uploaded manuals must not be used to train general AI models unless the user clearly agrees.
- The writer must be able to delete a manual and its test results.
- The product must explain how long files and reports are kept.
- All main actions must work with a keyboard.
- Results must use words and labels, not color alone.
- Error messages and instructions must use plain language.
- UVTS must clearly explain that its results are suggestions and do not replace legal, safety, or expert review.

## 11. What is Not Included in the First Version?

- Testing more than one manual at the same time
- Manuals longer than 20 pages
- Word documents, websites, videos, or other file types
- Scanned PDFs that need text recognition
- Checking whether statements in the manual are factually correct
- Testing the product interface or watching real users
- Editing individual generated questions
- Comparing two versions of a manual
- Team comments and approval steps
- Downloading reports
- Connections to support, document, or project-management tools

## 12. Risks and How UVTS Should Handle Them

### AI judgment may not match a human judgment

UVTS should show its reasoning in simple terms: what information was needed, what was found, what was missing, and which pages were used. The writer can then judge whether the result makes sense.

### Questions may focus too much on information already in the manual

UVTS should create some realistic edge-case questions that expose missing information. These questions must still relate to the product described in the manual.

### A strong result may create too much confidence

Every report should explain that UVTS checks whether information exists in the manual. A strong result does not prove that the information is correct, safe, complete for every possible user, or easy to follow.

### Some PDFs may be difficult to read

UVTS should reject files with no readable text and clearly explain the problem. Page references let the writer compare each result with the original manual.

### A new test may create different questions

UVTS saves the exact questions used in each test. Questions never change after that test begins.

## 13. How We Will Know the First Version Is Ready

The first version is ready for a small group of users when:

- A suitable 1-to-20-page PDF can complete the full journey from upload to report.
- Unsupported PDFs fail safely and show a useful message.
- The writer can create between 1 and 15 questions using all three question types.
- Every completed result shows an information-coverage status and real page evidence when information is found.
- The report clearly shows missing information and useful recommendations.
- Writers without technical knowledge can understand the setup and report during user testing.
- Human reviewers test a sample group of manuals and agree that most results are reasonable.
- Privacy, deletion, keyboard use, and readable status labels have been tested.

## 14. Possible Future Features

- Support for scanned PDFs
- Longer manuals and more than one manual per test
- Custom question types, topics, and user viewpoints
- Editing or adding individual questions
- Saved test setups
- Comparing old and new versions of a manual
- Downloadable and shareable reports
- Team review and approval tools
- Connections to support-ticket and documentation systems
- Separate checks for readability, consistency, and factual accuracy

## 15. Decisions Still Needed

Before development begins, the team must decide:

- Whether users need an account
- The largest allowed PDF file size
- How long manuals and reports are kept
- Whether a writer can stop a test while it is running
- The expected waiting time for question generation and testing
- How the team will check that UVTS results are accurate enough for release
- Which database and durable-job system will preserve tests and completed results
- How the Vite application and FastAPI service will be hosted and connected in each environment
- Which browser versions the first release must support
