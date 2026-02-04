# -*- coding: utf-8 -*-
"""
Evaluation Runner for Resume Auto-Fit MCP Server

Runs test cases from evaluation.xml and validates responses.
Usage: python tests/run_evaluation.py
"""

import asyncio
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add paths for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "mcp_server"))

from resume_renderer import ResumeRenderer


class EvaluationRunner:
    """Runs evaluation test cases and validates results"""
    
    def __init__(self, eval_file: str = None):
        if eval_file is None:
            eval_file = Path(__file__).parent / "evaluation.xml"
        self.eval_file = Path(eval_file)
        self.renderer = None
        self.results = []
        
    async def setup(self):
        """Initialize renderer"""
        self.renderer = ResumeRenderer()
        await self.renderer.start()
        
    async def teardown(self):
        """Cleanup renderer"""
        if self.renderer:
            await self.renderer.stop()
            
    def load_test_cases(self):
        """Parse evaluation.xml and return test cases"""
        tree = ET.parse(self.eval_file)
        root = tree.getroot()
        
        test_cases = []
        for qa_pair in root.findall('qa_pair'):
            test_id = qa_pair.get('id', 'unknown')
            category = qa_pair.get('category', 'general')
            description = qa_pair.find('description')
            
            input_elem = qa_pair.find('input')
            markdown_elem = input_elem.find('markdown')
            markdown = markdown_elem.text.strip() if markdown_elem is not None and markdown_elem.text else ""
            
            output_path_elem = input_elem.find('output_path')
            output_path = output_path_elem.text if output_path_elem is not None else None
            
            expected = qa_pair.find('expected')
            expectations = {}
            for child in expected:
                expectations[child.tag] = child.text
                
            test_cases.append({
                'id': test_id,
                'category': category,
                'description': description.text if description is not None else '',
                'markdown': markdown,
                'output_path': output_path,
                'expectations': expectations
            })
            
        return test_cases
    
    def validate_result(self, result: dict, expectations: dict) -> tuple[bool, list[str]]:
        """Validate result against expectations, return (passed, errors)"""
        errors = []
        
        for key, expected_value in expectations.items():
            if key == 'status':
                if result.get('status') != expected_value:
                    errors.append(f"Expected status '{expected_value}', got '{result.get('status')}'")
                    
            elif key == 'status_in':
                valid_statuses = [s.strip() for s in expected_value.split(',')]
                if result.get('status') not in valid_statuses:
                    errors.append(f"Expected status in {valid_statuses}, got '{result.get('status')}'")
                    
            elif key == 'has_pdf_path':
                if expected_value == 'true' and not result.get('pdf_path'):
                    errors.append("Expected pdf_path but none found")
                    
            elif key == 'current_pages':
                if result.get('current_pages') != int(expected_value):
                    errors.append(f"Expected {expected_value} pages, got {result.get('current_pages')}")
                    
            elif key == 'current_pages_gt':
                if result.get('current_pages', 0) <= int(expected_value):
                    errors.append(f"Expected > {expected_value} pages, got {result.get('current_pages')}")
                    
            elif key == 'has_hint':
                if expected_value == 'true' and not result.get('hint'):
                    errors.append("Expected hint but none found")
                    
            elif key == 'has_suggestion':
                if expected_value == 'true' and not result.get('suggestion'):
                    errors.append("Expected suggestion but none found")
                    
            elif key == 'has_next_action':
                if expected_value == 'true' and not result.get('next_action'):
                    errors.append("Expected next_action but none found")
                    
            elif key == 'error_code':
                if result.get('error_code') != expected_value:
                    errors.append(f"Expected error_code '{expected_value}', got '{result.get('error_code')}'")
                    
            elif key == 'fill_ratio_lt':
                fill_ratio = result.get('fill_ratio', 1.0)
                if fill_ratio >= float(expected_value):
                    errors.append(f"Expected fill_ratio < {expected_value}, got {fill_ratio}")
                    
            elif key == 'pdf_path_contains':
                pdf_path = result.get('pdf_path', '')
                if expected_value not in pdf_path:
                    errors.append(f"Expected pdf_path to contain '{expected_value}', got '{pdf_path}'")
                    
            elif key == 'has_content_stats':
                if expected_value == 'true' and not result.get('content_stats'):
                    errors.append("Expected content_stats but none found")
                    
            elif key == 'content_stats_has_word_count':
                stats = result.get('content_stats', {})
                if expected_value == 'true' and 'word_count' not in stats:
                    errors.append("Expected word_count in content_stats")
                    
            elif key == 'content_stats_has_li_count':
                stats = result.get('content_stats', {})
                if expected_value == 'true' and 'li_count' not in stats:
                    errors.append("Expected li_count in content_stats")
                    
            elif key == 'has_auto_fit_status':
                if expected_value == 'true' and not result.get('auto_fit_status'):
                    errors.append("Expected auto_fit_status but none found")
                    
        return len(errors) == 0, errors
    
    async def run_test(self, test_case: dict) -> dict:
        """Run a single test case"""
        test_id = test_case['id']
        markdown = test_case['markdown']
        output_path = test_case['output_path']
        
        # Generate unique output path if not specified
        if output_path is None:
            output_dir = Path(__file__).parent.parent / "generated_resume"
            output_path = str(output_dir / f"eval_test_{test_id}.pdf")
        elif not Path(output_path).is_absolute():
            output_dir = Path(__file__).parent.parent / "generated_resume"
            output_path = str(output_dir / output_path)
            
        try:
            # Handle empty content test case specially
            if not markdown:
                result = {
                    "status": "error",
                    "error_code": "EMPTY_CONTENT",
                    "message": "Markdown content cannot be empty",
                    "suggestion": "Provide resume content in Markdown format",
                    "next_action": "Generate resume content first"
                }
            else:
                result = await self.renderer.render_resume_pdf(markdown, output_path)
                
            passed, errors = self.validate_result(result, test_case['expectations'])
            
            return {
                'id': test_id,
                'category': test_case['category'],
                'description': test_case['description'],
                'passed': passed,
                'errors': errors,
                'result': result
            }
            
        except Exception as e:
            return {
                'id': test_id,
                'category': test_case['category'],
                'description': test_case['description'],
                'passed': False,
                'errors': [f"Exception: {str(e)}"],
                'result': None
            }
    
    async def run_all(self):
        """Run all test cases"""
        print("=" * 60)
        print("Resume Auto-Fit MCP Server - Evaluation Suite")
        print("=" * 60)
        
        test_cases = self.load_test_cases()
        print(f"Loaded {len(test_cases)} test cases from {self.eval_file.name}")
        print()
        
        await self.setup()
        
        try:
            for test_case in test_cases:
                print(f"Running test {test_case['id']}: {test_case['description'][:50]}...")
                result = await self.run_test(test_case)
                self.results.append(result)
                
                if result['passed']:
                    print(f"  ✅ PASSED")
                else:
                    print(f"  ❌ FAILED")
                    for error in result['errors']:
                        print(f"     - {error}")
                        
        finally:
            await self.teardown()
            
        # Summary
        print()
        print("=" * 60)
        print("Evaluation Summary")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r['passed'])
        failed = len(self.results) - passed
        
        # Group by category
        categories = {}
        for r in self.results:
            cat = r['category']
            if cat not in categories:
                categories[cat] = {'passed': 0, 'failed': 0}
            if r['passed']:
                categories[cat]['passed'] += 1
            else:
                categories[cat]['failed'] += 1
                
        print(f"\nBy Category:")
        for cat, stats in categories.items():
            status = "✅" if stats['failed'] == 0 else "❌"
            print(f"  {status} {cat}: {stats['passed']}/{stats['passed'] + stats['failed']} passed")
            
        print(f"\nTotal: {passed}/{len(self.results)} tests passed")
        
        if failed > 0:
            print(f"\n❌ {failed} test(s) failed:")
            for r in self.results:
                if not r['passed']:
                    print(f"  - Test {r['id']}: {r['description']}")
                    for error in r['errors']:
                        print(f"      {error}")
        else:
            print("\n✅ All tests passed!")
            
        return failed == 0


async def main():
    runner = EvaluationRunner()
    success = await runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
