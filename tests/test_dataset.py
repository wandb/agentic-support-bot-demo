"""
Tests for evaluation dataset structure and coverage.

These tests validate that the dataset meets all requirements:
- At least 50 test cases
- Proper structure (required fields)
- Coverage requirements (refusals, tool usage, W&B questions)
- Data quality (valid tool names, diverse types)
"""

import sys
from pathlib import Path

# Add examples directory to path to import dataset
examples_dir = Path(__file__).parent.parent / "examples" / "step-4"
sys.path.insert(0, str(examples_dir))

from dataset import EVALUATION_DATASET


class TestDatasetStructure:
    """Test dataset structure and required fields."""
    
    def test_dataset_size(self):
        """Dataset must have at least 50 test cases."""
        assert len(EVALUATION_DATASET) >= 50, \
            f"Dataset must have at least 50 cases, has {len(EVALUATION_DATASET)}"
    
    def test_all_rows_have_required_fields(self):
        """All rows must have input, expected_output_description, and expected_tools."""
        for i, case in enumerate(EVALUATION_DATASET):
            assert "input" in case, f"Row {i} missing 'input'"
            assert "expected_output_description" in case, f"Row {i} missing 'expected_output_description'"
            assert "expected_tools" in case, f"Row {i} missing 'expected_tools'"
    
    def test_input_is_string(self):
        """All inputs must be strings."""
        for i, case in enumerate(EVALUATION_DATASET):
            assert isinstance(case["input"], str), \
                f"Row {i} input must be string, got {type(case['input'])}"
            assert len(case["input"]) > 0, f"Row {i} input cannot be empty"
    
    def test_expected_output_description_is_string(self):
        """All expected output descriptions must be strings."""
        for i, case in enumerate(EVALUATION_DATASET):
            expected = case["expected_output_description"]
            assert isinstance(expected, (str, dict)), \
                f"Row {i} expected_output_description must be string or dict, got {type(expected)}"
    
    def test_expected_tools_is_list(self):
        """All expected_tools must be lists."""
        for i, case in enumerate(EVALUATION_DATASET):
            tools = case["expected_tools"]
            assert isinstance(tools, list), \
                f"Row {i} expected_tools must be list, got {type(tools)}"


class TestDatasetCoverage:
    """Test that dataset covers required scenarios."""
    
    def test_refusal_coverage(self):
        """At least 5 refusal scenarios (off-topic/inappropriate)."""
        refusal_cases = [c for c in EVALUATION_DATASET if "refusal" in c.get("tags", [])]
        assert len(refusal_cases) >= 5, \
            f"Need at least 5 refusal cases, have {len(refusal_cases)}"
    
    def test_tool_usage_coverage(self):
        """At least 10 cases require tool usage."""
        tool_cases = [c for c in EVALUATION_DATASET if len(c["expected_tools"]) > 0]
        assert len(tool_cases) >= 10, \
            f"Need at least 10 tool usage cases, have {len(tool_cases)}"
    
    def test_wandb_question_coverage(self):
        """At least 10 realistic W&B/Weave questions."""
        wandb_cases = [
            c for c in EVALUATION_DATASET 
            if "weave" in c.get("tags", []) or "wandb" in c.get("tags", [])
        ]
        assert len(wandb_cases) >= 10, \
            f"Need at least 10 W&B questions, have {len(wandb_cases)}"
    
    def test_diverse_question_types(self):
        """Dataset should have diverse question types."""
        # Get all unique tags
        all_tags = set()
        for case in EVALUATION_DATASET:
            all_tags.update(case.get("tags", []))
        
        # Should have several different types of tags
        assert len(all_tags) >= 10, \
            f"Dataset should have diverse tags, only has {len(all_tags)}: {all_tags}"
        
        # Check for specific important types
        important_types = ["factual", "procedural", "troubleshooting", "refusal"]
        for type_tag in important_types:
            matching = [c for c in EVALUATION_DATASET if type_tag in c.get("tags", [])]
            assert len(matching) > 0, f"No cases tagged with '{type_tag}'"


class TestDatasetQuality:
    """Test dataset data quality."""
    
    def test_tool_names_are_valid(self):
        """Tool names should follow expected format."""
        valid_tools = {
            "support-create_issue",
            "support-get_issue"
        }
        
        for i, case in enumerate(EVALUATION_DATASET):
            for tool in case["expected_tools"]:
                assert tool in valid_tools, \
                    f"Row {i} has invalid tool name: {tool}. Valid: {valid_tools}"
    
    def test_no_empty_inputs(self):
        """No test case should have empty input."""
        for i, case in enumerate(EVALUATION_DATASET):
            assert case["input"].strip() != "", \
                f"Row {i} has empty input"
    
    def test_no_empty_expected_output_descriptions(self):
        """No test case should have empty expected output description."""
        for i, case in enumerate(EVALUATION_DATASET):
            expected = case["expected_output_description"]
            if isinstance(expected, str):
                assert expected.strip() != "", \
                    f"Row {i} has empty expected_output_description"
            elif isinstance(expected, dict):
                assert len(expected) > 0, \
                    f"Row {i} has empty expected_output_description dict"
    
    def test_tags_are_lowercase(self):
        """Tags should be lowercase for consistency."""
        for i, case in enumerate(EVALUATION_DATASET):
            for tag in case.get("tags", []):
                assert tag.islower() or "-" in tag or "_" in tag, \
                    f"Row {i} has non-lowercase tag: {tag}"


class TestSpecificScenarios:
    """Test that specific important scenarios are covered."""
    
    def test_ticket_creation_scenarios(self):
        """Should have multiple ticket creation scenarios."""
        create_cases = [
            c for c in EVALUATION_DATASET 
            if "support-create_issue" in c["expected_tools"]
        ]
        assert len(create_cases) >= 5, \
            f"Need at least 5 ticket creation cases, have {len(create_cases)}"
    
    def test_ticket_retrieval_scenarios(self):
        """Should have multiple ticket retrieval scenarios."""
        get_cases = [
            c for c in EVALUATION_DATASET 
            if "support-get_issue" in c["expected_tools"]
        ]
        assert len(get_cases) >= 3, \
            f"Need at least 3 ticket retrieval cases, have {len(get_cases)}"
    
    def test_off_topic_refusals(self):
        """Should have off-topic questions that should be refused."""
        off_topic = [
            c for c in EVALUATION_DATASET 
            if "off-topic" in c.get("tags", [])
        ]
        assert len(off_topic) >= 5, \
            f"Need at least 5 off-topic refusal cases, have {len(off_topic)}"
    
    def test_adversarial_refusals(self):
        """Should have adversarial inputs that should be refused."""
        adversarial = [
            c for c in EVALUATION_DATASET 
            if "adversarial" in c.get("tags", [])
        ]
        assert len(adversarial) >= 3, \
            f"Need at least 3 adversarial cases, have {len(adversarial)}"
    
    def test_weave_initialization_questions(self):
        """Should have questions about Weave initialization."""
        init_cases = [
            c for c in EVALUATION_DATASET 
            if "initialization" in c.get("tags", []) or
               "init" in c["input"].lower()
        ]
        assert len(init_cases) >= 2, \
            f"Need at least 2 Weave initialization questions, have {len(init_cases)}"

