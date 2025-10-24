#!/usr/bin/env python3
"""
Publish the evaluation dataset to Weave.

This script loads the dataset from dataset.py and publishes it to Weave
for versioning and tracking. The published dataset can then be used by
the evaluation script.

Usage:
    uv run python examples/step-4-complete/publish_dataset.py
"""

import os
import sys
from dotenv import load_dotenv
import weave

# Add parent directory to path to import dataset
sys.path.insert(0, os.path.dirname(__file__))
from dataset import EVALUATION_DATASET, validate_dataset


def main():
    """Publish evaluation dataset to Weave."""
    
    print("=" * 60)
    print("Publishing Evaluation Dataset to Weave")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variable
    if not os.getenv("WANDB_API_KEY"):
        print("❌ Error: WANDB_API_KEY environment variable not set")
        print()
        print("Please set your W&B API key:")
        print("  1. Create a .env file from .env.example")
        print("  2. Add WANDB_API_KEY=your_key_here")
        print("  3. Or export WANDB_API_KEY=your_key_here")
        print()
        print("Get your API key at: https://wandb.ai/authorize")
        sys.exit(1)
    
    # Validate dataset before publishing
    print("Validating dataset...")
    try:
        validate_dataset()
        print()
    except AssertionError as e:
        print(f"❌ Dataset validation failed: {e}")
        sys.exit(1)
    
    # Initialize Weave
    print("Initializing Weave...")
    try:
        weave.init("agentic-support-bot-demo")
        print("✓ Connected to Weave project: agentic-support-bot-demo")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize Weave: {e}")
        print()
        print("Please check:")
        print("  - WANDB_API_KEY is valid")
        print("  - You have internet connection")
        print("  - W&B service is accessible")
        sys.exit(1)
    
    # Publish dataset
    print(f"Publishing dataset with {len(EVALUATION_DATASET)} test cases...")
    try:
        dataset = weave.Dataset(
            name="support-bot-eval-dataset",
            rows=EVALUATION_DATASET
        )
        
        # Publish the dataset
        weave.publish(dataset)
        
        print("✓ Dataset published successfully!")
        print()
        print("Dataset details:")
        print(f"  - Name: support-bot-eval-dataset")
        print(f"  - Total cases: {len(EVALUATION_DATASET)}")
        print(f"  - Refusal scenarios: {len([c for c in EVALUATION_DATASET if 'refusal' in c.get('tags', [])])}")
        print(f"  - Tool usage cases: {len([c for c in EVALUATION_DATASET if c['expected_tools']])}")
        print(f"  - W&B questions: {len([c for c in EVALUATION_DATASET if 'weave' in c.get('tags', []) or 'wandb' in c.get('tags', [])])}")
        print()
        print("=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. View dataset in Weave UI:")
        print("   https://wandb.ai/")
        print("   Navigate to: agentic-support-bot-demo → Datasets tab")
        print()
        print("2. Run evaluation:")
        print("   uv run python examples/step-4-complete/run_evaluation.py")
        print()
        
    except Exception as e:
        print(f"❌ Failed to publish dataset: {e}")
        print()
        print("This might be due to:")
        print("  - Network issues")
        print("  - W&B API problems")
        print("  - Dataset format issues")
        sys.exit(1)


if __name__ == "__main__":
    main()

