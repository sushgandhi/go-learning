# Required libraries:
# pip install langgraph langchain-core pandas openpyxl

from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
import pandas as pd
import re # For parsing LLM output

# --- 0. LLM Placeholder ---
# Replace this with your actual LLM client (e.g., from langchain_community.chat_models)
class DummyLLM:
    """
    A dummy LLM to simulate responses. Replace with a real LLM client.
    Example: from langchain_community.chat_models import ChatOllama
             llm = ChatOllama(model="llama3")
    """
    def invoke(self, prompt: str) -> str:
        print(f"\n--- DUMMY LLM INVOKED WITH PROMPT (first 200 chars) ---\n{prompt[:200]}...\n-----------------------------------\n")
        # Simulate responses based on prompt content
        if "Analyze the following text data" in prompt and "Anomaly" in prompt: # Unsupervised
            if "critical" in prompt.lower() or "error" in prompt.lower():
                return "Category: Anomaly\nReasoning: Contains critical keywords."
            elif "strange data" in prompt.lower():
                return "Category: Anomaly\nReasoning: Data appears unusual."
            elif not re.search(r"\'([^']+)\'", prompt).group(1).strip(): # Check if text_to_classify is empty
                 return "Category: Empty/Invalid\nReasoning: The input text was empty."
            return "Category: General Observation\nReasoning: Appears to be a standard entry."
        elif "Given the following examples" in prompt: # Few-shot
            if "urgent" in prompt.lower() or "asap" in prompt.lower():
                return "Category: Urgent"
            elif "question" in prompt.lower():
                return "Category: Inquiry"
            return "Category: General"
        elif "Use the following category definitions" in prompt: # Definition-based
            # This is a very simplistic simulation. A real LLM would use the definitions.
            if "financial loss" in prompt.lower():
                return "Category: High Risk" # Assuming High Risk was a defined category
            elif "customer satisfaction" in prompt.lower():
                return "Category: Feedback"
            return "Category: Uncategorized"
        return "Category: Simulated Fallback\nReasoning: No specific simulation rule matched."

# --- 1. Define the State ---
class ExcelRowClassificationState(TypedDict):
    """
    Represents the state of the Excel row classification workflow.
    """
    all_rows_data: Optional[List[Dict[str, Any]]]
    provided_examples: Optional[List[Dict[str, Any]]]
    class_definitions: Optional[Dict[str, str]]
    target_column_for_classification: str
    label_column_name: Optional[str]

    input_row: Dict[str, Any]

    classification_mode: Optional[str]
    llm_prompt: Optional[str]
    classification_category: Optional[str]
    confidence_score: Optional[float] # Note: Confidence from LLMs can be tricky.
    llm_reasoning: Optional[str]
    error_message: Optional[str]
    processing_steps: List[str]

# --- 2. Define Agent/Nodes ---

def determine_classification_strategy(state: ExcelRowClassificationState) -> ExcelRowClassificationState:
    """
    Determines the classification strategy based on provided examples or definitions.
    This node now assumes `target_column_for_classification` and potentially
    `provided_examples` or `class_definitions` are already set in the initial state
    when the graph is invoked for each row.
    """
    print("---DETERMINING CLASSIFICATION STRATEGY---")
    current_steps = state.get("processing_steps", [])
    examples = state.get("provided_examples")
    definitions = state.get("class_definitions")
    target_col = state.get("target_column_for_classification")
    label_col = state.get("label_column_name") # Used for validating examples if present

    if not target_col: # Should be set by the main script
        state["error_message"] = "Critical: `target_column_for_classification` is not set in the state."
        state["processing_steps"] = current_steps + ["determine_classification_strategy: FAILED - No target column"]
        return state

    if examples: # Examples are assumed to be pre-validated by the main script
        state["classification_mode"] = "few_shot_examples"
        print(f"Strategy: Few-shot with {len(examples)} examples.")
        state["processing_steps"] = current_steps + ["determine_classification_strategy: SUCCESS - Few-shot"]
        return state

    if definitions and isinstance(definitions, dict) and definitions:
        state["classification_mode"] = "definition_based"
        print(f"Strategy: Definition-based with {len(definitions)} definitions.")
        state["processing_steps"] = current_steps + ["determine_classification_strategy: SUCCESS - Definition-based"]
        return state
    
    state["classification_mode"] = "unsupervised_anomaly"
    print("Strategy: Unsupervised / Anomaly Detection (no valid examples or definitions found).")
    state["processing_steps"] = current_steps + ["determine_classification_strategy: SUCCESS - Unsupervised"]
    return state

def validate_row_data(state: ExcelRowClassificationState) -> ExcelRowClassificationState:
    print("---VALIDATING ROW DATA---")
    current_steps = state.get("processing_steps", [])
    if state.get("error_message"):
        state["processing_steps"] = current_steps + ["validate_row_data: SKIPPED due to prior error"]
        return state

    input_row = state.get("input_row")
    target_col = state.get("target_column_for_classification")

    if not input_row:
        state["error_message"] = "Input row is missing."
        state["processing_steps"] = current_steps + ["validate_row_data: FAILED - No input row"]
        return state

    if target_col not in input_row:
        state["error_message"] = f"Target column '{target_col}' not found in the input row: {list(input_row.keys())}."
        state["processing_steps"] = current_steps + [f"validate_row_data: FAILED - Missing target column '{target_col}'"]
        return state

    if not isinstance(input_row.get(target_col), str):
        # Attempt to convert to string if it's not, e.g. a number read from Excel
        try:
            input_row[target_col] = str(input_row[target_col])
            print(f"Warning: Target column '{target_col}' was not a string, converted to: '{input_row[target_col]}'")
            current_steps.append(f"validate_row_data: WARNING - Converted target column to string")
        except Exception:
            state["error_message"] = f"Target column '{target_col}' is not a string and could not be converted. Value: {input_row.get(target_col)} (Type: {type(input_row.get(target_col))})."
            state["processing_steps"] = current_steps + [f"validate_row_data: FAILED - Invalid type for '{target_col}'"]
            return state


    print(f"Row data validated. Text to classify: '{str(input_row.get(target_col))[:50]}...'")
    state["processing_steps"] = current_steps + ["validate_row_data: SUCCESS"]
    return state

def prepare_llm_input_node(state: ExcelRowClassificationState) -> ExcelRowClassificationState:
    print("---PREPARING LLM INPUT---")
    current_steps = state.get("processing_steps", [])
    if state.get("error_message"):
        state["processing_steps"] = current_steps + ["prepare_llm_input_node: SKIPPED due to error"]
        return state

    mode = state["classification_mode"]
    row_data = state["input_row"]
    target_col = state["target_column_for_classification"]
    text_to_classify = str(row_data.get(target_col, "")) # Ensure it's a string

    prompt = ""
    if mode == "unsupervised_anomaly":
        prompt = (
            f"Analyze the following text data from a dataset: '{text_to_classify}'.\n"
            "Identify its key characteristics. Based on these, would you consider this data point "
            "an anomaly, or can you suggest a general category it might belong to? "
            "Respond with 'Category: <Your Category>' and on a new line 'Reasoning: <Your Reasoning>'. "
            "If anomalous, state 'Category: Anomaly'. If the text is empty or clearly invalid, state 'Category: Empty/Invalid'."
        )
    elif mode == "few_shot_examples":
        examples = state["provided_examples"]
        label_col = state["label_column_name"] # This is the key for the label in the example dict
        
        # Ensure target_col and label_col are correctly referenced for examples
        formatted_examples = "\n".join(
            [f"- Text: \"{ex.get(target_col, '')}\" -> Category: {ex.get(label_col, 'UnknownLabel')}" for ex in examples]
        )
        categories = set(ex.get(label_col, 'UnknownLabel') for ex in examples)
        prompt = (
            f"You are an expert text classifier. Given the following examples (categories seen: {', '.join(sorted(list(categories)))}):\n"
            f"{formatted_examples}\n\n"
            f"Now, classify the following text: '{text_to_classify}'\n"
            "Provide only the category name from the examples. If unsure or if it doesn't fit, state 'Uncertain'.\n"
            "Category:"
        )
    elif mode == "definition_based":
        definitions = state["class_definitions"]
        formatted_definitions = "\n".join(
            [f"- {cat}: {desc}" for cat, desc in definitions.items()]
        )
        category_names = list(definitions.keys())
        prompt = (
            "You are an expert text classifier. Use ONLY the following category definitions to classify the text below:\n\n"
            "Definitions:\n"
            f"{formatted_definitions}\n\n"
            f"Text to classify: '{text_to_classify}'\n"
            f"Provide the most fitting category name from this list: {', '.join(category_names)}. If none fit well, state 'Uncategorized'.\n"
            "Category:"
        )
    else:
        state["error_message"] = f"Unknown classification mode: {mode}"
        state["processing_steps"] = current_steps + [f"prepare_llm_input_node: FAILED - Unknown mode {mode}"]
        return state

    state["llm_prompt"] = prompt
    # print(f"LLM Prompt for mode '{mode}':\n{prompt}") # Full prompt for debugging
    state["processing_steps"] = current_steps + [f"prepare_llm_input_node: SUCCESS - Mode {mode}"]
    return state

def llm_classification_agent(state: ExcelRowClassificationState, llm_client: Any) -> ExcelRowClassificationState:
    """
    Node representing the LLM classification agent.
    Uses the provided llm_client to make the call.
    """
    print("---LLM CLASSIFICATION AGENT---")
    current_steps = state.get("processing_steps", [])
    if state.get("error_message") or not state.get("llm_prompt"):
        print("Skipping LLM classification due to previous error or missing prompt.")
        state["processing_steps"] = current_steps + ["llm_classification_agent: SKIPPED"]
        return state

    prompt = state["llm_prompt"]
    mode = state["classification_mode"]
    
    try:
        print(f"Calling LLM for mode '{mode}'...")
        raw_llm_response = llm_client.invoke(prompt) # ACTUAL LLM CALL
        print(f"Raw LLM Response: {raw_llm_response}")

        # Parse the LLM response
        parsed_category = "Error: Parsing Failed"
        parsed_reasoning = None
        # Default confidence, real confidence from LLM is complex to get reliably for all models/prompts
        parsed_confidence = 0.75 

        if isinstance(raw_llm_response, str):
            raw_llm_response = raw_llm_response.strip()
            if mode == "unsupervised_anomaly":
                category_match = re.search(r"Category:\s*(.*)", raw_llm_response, re.IGNORECASE)
                reasoning_match = re.search(r"Reasoning:\s*(.*)", raw_llm_response, re.IGNORECASE)
                if category_match:
                    parsed_category = category_match.group(1).strip()
                if reasoning_match:
                    parsed_reasoning = reasoning_match.group(1).strip()
                if parsed_category == "Anomaly": parsed_confidence = 0.9
                elif parsed_category == "Empty/Invalid": parsed_confidence = 0.5
                else: parsed_confidence = 0.65

            elif mode in ["few_shot_examples", "definition_based"]:
                # Expecting the category directly, or "Category: <name>"
                if raw_llm_response.lower().startswith("category:"):
                    parsed_category = raw_llm_response.split(":", 1)[1].strip()
                else:
                    parsed_category = raw_llm_response # Assume the whole response is the category
                
                # Basic confidence simulation
                if parsed_category == "Uncertain" or parsed_category == "Uncategorized":
                    parsed_confidence = 0.4
                elif state.get("class_definitions") and parsed_category in state["class_definitions"]:
                     parsed_confidence = 0.85 # Higher if it's a defined category
                elif state.get("provided_examples") and any(ex.get(state["label_column_name"]) == parsed_category for ex in state["provided_examples"]):
                    parsed_confidence = 0.88 # Higher if it's an example category
                else:
                    parsed_confidence = 0.60


            state["classification_category"] = parsed_category
            state["llm_reasoning"] = parsed_reasoning if parsed_reasoning else "N/A"
            state["confidence_score"] = parsed_confidence

        else: # Handle if LLM response is not a string (e.g. AIMessage object)
            # This part would need to be adapted based on the actual LLM client library used
            # For example, if it's an AIMessage: raw_llm_response.content
            state["error_message"] = "LLM response was not a string. Cannot parse."
            state["classification_category"] = "Error: LLM Output Type"
            state["llm_reasoning"] = str(raw_llm_response)


    except Exception as e:
        print(f"Error during LLM call or parsing: {e}")
        state["error_message"] = f"LLM call/parsing failed: {str(e)}"
        state["classification_category"] = "Error: LLM Exception"
        state["llm_reasoning"] = None
        state["confidence_score"] = 0.0

    state["processing_steps"] = current_steps + [f"llm_classification_agent: {state['classification_category'] if not state.get('error_message') else 'FAILED'}"]
    return state

def quality_check_node(state: ExcelRowClassificationState) -> ExcelRowClassificationState:
    print("---QUALITY CHECK---")
    current_steps = state.get("processing_steps", [])
    if state.get("error_message"):
        state["processing_steps"] = current_steps + ["quality_check_node: SKIPPED"]
        return state

    confidence = state.get("confidence_score", 0.0)
    category = state.get("classification_category", "")

    # Check for error categories from LLM parsing or call
    if category and "Error:" in category:
        print(f"Category '{category}' indicates an error. Flagging for review.")
        state["classification_category"] = f"Review_Needed: {category}"
        state["processing_steps"] = current_steps + [f"quality_check_node: FLAGGED FOR REVIEW - {category}"]
    elif category == "Uncertain" or category == "Uncategorized" or category == "Empty/Invalid":
        print(f"Category '{category}' indicates uncertainty or invalid data. Flagging for review.")
        state["classification_category"] = f"Review_Needed: {category}"
        state["processing_steps"] = current_steps + [f"quality_check_node: FLAGGED FOR REVIEW - {category}"]
    elif confidence is not None and confidence < 0.65: # Adjusted threshold
        print(f"Low confidence ({confidence:.2f}) for category '{category}'. Flagging for review.")
        state["classification_category"] = f"Review_Needed: {category} (Low Confidence)"
        state["processing_steps"] = current_steps + ["quality_check_node: FLAGGED FOR REVIEW - Low Confidence"]
    else:
        state["processing_steps"] = current_steps + ["quality_check_node: PASSED"]
    return state

def decide_next_step(state: ExcelRowClassificationState) -> str:
    print("---DECIDING NEXT STEP---")
    if state.get("error_message"): # Check for errors from any previous step
        print(f"Error detected: {state['error_message']}. Routing to error handler.")
        return "handle_error"

    # No need to check classification_category for "Error:" here, as error_message should be set.
    if state.get("classification_category", "").startswith("Review_Needed"):
        print("Classification needs review. Ending here (could route to a review queue).")
        return END 
    
    print("Processing seems fine. Moving to END.")
    return END

def error_handling_node(state: ExcelRowClassificationState) -> ExcelRowClassificationState:
    print("---ERROR HANDLER---")
    current_steps = state.get("processing_steps", [])
    error = state.get("error_message", "Unknown error")
    print(f"An error occurred during processing: {error}")
    state["processing_steps"] = current_steps + [f"error_handling_node: Logged - {error}"]
    # Ensure error is reflected in final output if not already
    if not state.get("classification_category", "").startswith("Error:"):
        state["classification_category"] = f"Error: {error}"
    state["confidence_score"] = 0.0
    return state

# --- 3. Construct the Graph ---
def create_graph(llm_client: Any) -> StateGraph:
    workflow = StateGraph(ExcelRowClassificationState)

    workflow.add_node("strategy_determiner", determine_classification_strategy)
    workflow.add_node("row_validator", validate_row_data)
    workflow.add_node("prompt_preparer", prepare_llm_input_node)
    # Pass the llm_client to the node that needs it
    workflow.add_node("llm_classifier", lambda state: llm_classification_agent(state, llm_client))
    workflow.add_node("quality_checker", quality_check_node)
    workflow.add_node("error_handler", error_handling_node)

    workflow.set_entry_point("strategy_determiner")
    workflow.add_edge("strategy_determiner", "row_validator")
    workflow.add_edge("row_validator", "prompt_preparer")
    workflow.add_edge("prompt_preparer", "llm_classifier")
    workflow.add_edge("llm_classifier", "quality_checker")

    workflow.add_conditional_edges(
        "quality_checker",
        decide_next_step,
        {
            "handle_error": "error_handler",
            END: END
        }
    )
    workflow.add_edge("error_handler", END)
    return workflow.compile()

# --- 4. Main Execution Logic ---
if __name__ == "__main__":
    print("--- Excel Row Classification Agent ---")

    # Initialize LLM (Replace with your actual LLM setup)
    llm = DummyLLM()
    # Example for a real LLM:
    # try:
    #     from langchain_community.chat_models import ChatOllama
    #     llm = ChatOllama(model="llama3") # or your preferred model
    #     llm.invoke("test") # Quick test
    #     print("Successfully initialized ChatOllama.")
    # except Exception as e:
    #     print(f"Could not initialize LLM. Using DummyLLM. Error: {e}")
    #     llm = DummyLLM()


    # Get user inputs
    input_file_path = input("Enter the path to your input Excel/CSV file: ")
    output_file_path = input("Enter the path for your output Excel/CSV file: ")
    target_column = input("Enter the name of the column containing the text to classify: ")

    user_class_definitions = None
    user_provided_examples = None
    user_label_column_name = None

    mode_choice = input("Choose mode: (1) Use examples from file, (2) Define categories, (3) Unsupervised: ").strip()

    if mode_choice == '1': # Examples from file
        user_label_column_name = input(f"Enter the name of the column in '{input_file_path}' that contains existing labels for examples: ")
        print(f"Will use column '{user_label_column_name}' for examples.")
    elif mode_choice == '2': # Define categories
        user_class_definitions = {}
        print("Define your categories. Enter an empty category name when done.")
        while True:
            cat_name = input("Enter category name (e.g., 'Spam', 'Urgent'): ").strip()
            if not cat_name:
                break
            cat_def = input(f"Enter definition for '{cat_name}': ").strip()
            user_class_definitions[cat_name] = cat_def
        if not user_class_definitions:
            print("No definitions provided. Switching to unsupervised mode.")
            mode_choice = '3'
        else:
            print(f"Definitions received: {user_class_definitions}")

    # Read input file
    try:
        if input_file_path.endswith('.csv'):
            df = pd.read_csv(input_file_path)
        elif input_file_path.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(input_file_path)
        else:
            raise ValueError("Unsupported file type. Please use .csv, .xls, or .xlsx")
        print(f"Successfully read {len(df)} rows from '{input_file_path}'. Columns: {df.columns.tolist()}")
    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_file_path}'")
        exit()
    except Exception as e:
        print(f"Error reading input file: {e}")
        exit()

    # Prepare examples if mode is '1'
    if mode_choice == '1' and user_label_column_name:
        if user_label_column_name not in df.columns:
            print(f"Error: Label column '{user_label_column_name}' not found in the input file. Available columns: {df.columns.tolist()}")
            exit()
        if target_column not in df.columns: # Also check target column for examples
            print(f"Error: Target column '{target_column}' not found in the input file, cannot prepare examples.")
            exit()
            
        # Filter rows that have a label and use them as examples
        example_df = df[df[user_label_column_name].notna() & (df[user_label_column_name] != '')]
        if not example_df.empty:
            user_provided_examples = example_df[[target_column, user_label_column_name]].to_dict(orient="records")
            # Rename keys in examples to match what `prepare_llm_input_node` expects if needed,
            # but it's better if `target_column_for_classification` and `label_column_name` are used directly.
            # The current `prepare_llm_input_node` uses state.target_column_for_classification and state.label_column_name
            print(f"Found {len(user_provided_examples)} examples from the input file.")
            if not user_provided_examples: # Should not happen if example_df not empty
                 print("Warning: No valid examples extracted despite label column being present.")
        else:
            print(f"Warning: No rows found with labels in column '{user_label_column_name}'. Switching to unsupervised mode.")
            mode_choice = '3' # Fallback
            user_provided_examples = None
            user_label_column_name = None


    # Compile the graph
    app = create_graph(llm_client=llm) # Pass the LLM client to the graph factory

    results = []
    print(f"\n--- Starting classification for {len(df)} rows ---")
    for index, row in df.iterrows():
        print(f"\n--- Processing Row {index + 1} ---")
        input_row_dict = row.to_dict()

        initial_state: ExcelRowClassificationState = {
            "input_row": input_row_dict,
            "target_column_for_classification": target_column,
            "label_column_name": user_label_column_name, # Will be None if not in example mode
            "provided_examples": user_provided_examples, # Will be None if not in example mode
            "class_definitions": user_class_definitions, # Will be None if not in definition mode
            "all_rows_data": None, # Not used in this version
            "classification_mode": None, # To be set by strategy_determiner
            "llm_prompt": None,
            "classification_category": None,
            "confidence_score": None,
            "llm_reasoning": None,
            "error_message": None,
            "processing_steps": []
        }
        
        final_state = app.invoke(initial_state)
        
        # Store results
        output_row = input_row_dict.copy() # Start with original data
        output_row["classification_mode_used"] = final_state.get("classification_mode")
        output_row["llm_classification"] = final_state.get("classification_category")
        output_row["llm_confidence"] = final_state.get("confidence_score")
        output_row["llm_reasoning_output"] = final_state.get("llm_reasoning")
        output_row["processing_error"] = final_state.get("error_message")
        output_row["_processing_steps_log"] = " | ".join(final_state.get("processing_steps", []))
        results.append(output_row)

        print(f"--- Result for Row {index + 1} ---")
        print(f"  Input Text ('{target_column}'): {str(input_row_dict.get(target_column, 'N/A'))[:70]}...")
        print(f"  Mode: {output_row['classification_mode_used']}")
        print(f"  Classification: {output_row['llm_classification']}")
        print(f"  Confidence: {output_row['llm_confidence']:.2f}" if output_row['llm_confidence'] is not None else "  Confidence: N/A")
        if output_row['processing_error']:
            print(f"  Error: {output_row['processing_error']}")


    # Save results
    results_df = pd.DataFrame(results)
    try:
        if output_file_path.endswith('.csv'):
            results_df.to_csv(output_file_path, index=False)
        elif output_file_path.endswith(('.xls', '.xlsx')):
            results_df.to_excel(output_file_path, index=False)
        else:
            print(f"Warning: Output file path '{output_file_path}' has unsupported extension. Saving as CSV.")
            results_df.to_csv(output_file_path + ".csv", index=False) # Default to CSV
        print(f"\n--- Classification complete. Results saved to '{output_file_path}' ---")
    except Exception as e:
        print(f"Error writing output file: {e}")

    # Optional: Visualize graph
    # try:
    #     from IPython.display import Image, display
    #     graph_image = app.get_graph().draw_mermaid_png()
    #     if graph_image:
    #         with open("workflow_graph.png", "wb") as f:
    #             f.write(graph_image)
    #         print("\nGraph visualization saved to workflow_graph.png")
    #     else:
    #         print("\nFailed to generate graph visualization.")
    # except Exception as e:
    #     print(f"\nCould not visualize graph (is graphviz installed and in PATH? Is IPython available?): {e}")
    #     print("Mermaid graph definition:\n", app.get_graph().draw_mermaid())
