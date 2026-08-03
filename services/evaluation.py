"""
Evaluation Framework - Hallucination Detection & RAG Quality Metrics
Measures AI response accuracy and retrieval quality
"""

from typing import Dict, Any, List, Optional, Tuple
import re
from datetime import datetime
import json


class HallucinationDetector:
    """Detects hallucinations in AI responses by verifying against source data"""
    
    def __init__(self):
        self.hallucination_log: List[Dict[str, Any]] = []
    
    def detect_hallucinations(self, response: str, source_data: List[Dict[str, Any]], 
                             query: str = "") -> Dict[str, Any]:
        """
        Detect hallucinations in AI response
        
        Args:
            response: AI-generated response text
            source_data: Original Salesforce data used
            query: User's original query
            
        Returns:
            Dictionary with hallucination metrics
        """
        results = {
            "has_hallucination": False,
            "hallucination_score": 0.0,  # 0 = no hallucination, 1 = complete hallucination
            "issues": [],
            "verified_facts": 0,
            "unverified_facts": 0,
            "confidence": 0.0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Extract claims from response
        claims = self._extract_claims(response)
        
        if not claims:
            results["confidence"] = 0.5
            return results
        
        # Verify each claim against source data
        verified = 0
        unverified = 0
        
        for claim in claims:
            is_verified, issue = self._verify_claim(claim, source_data)
            
            if is_verified:
                verified += 1
            else:
                unverified += 1
                if issue:
                    results["issues"].append(issue)
        
        results["verified_facts"] = verified
        results["unverified_facts"] = unverified
        
        # Calculate hallucination score
        total_claims = verified + unverified
        if total_claims > 0:
            results["hallucination_score"] = unverified / total_claims
            results["has_hallucination"] = results["hallucination_score"] > 0.3
            results["confidence"] = verified / total_claims
        
        # Log if hallucination detected
        if results["has_hallucination"]:
            self._log_hallucination(query, response, results)
        
        return results
    
    def _extract_claims(self, response: str) -> List[str]:
        """Extract factual claims from response"""
        claims = []
        
        # Extract numerical claims (amounts, scores, counts)
        number_patterns = [
            r'\$[\d,]+',  # Dollar amounts
            r'\d+%',  # Percentages
            r'Score:?\s*\d+',  # Scores
            r'\d+\s+(?:leads?|opportunities|deals?)',  # Counts
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            claims.extend(matches)
        
        # Extract named entities (lead names, company names)
        # Simple pattern: capitalized words that might be names
        name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        names = re.findall(name_pattern, response)
        
        # Filter out common words
        common_words = {'The', 'This', 'That', 'These', 'Those', 'Lead', 'Opportunity', 
                       'Deal', 'Score', 'Stage', 'Status', 'Company'}
        names = [n for n in names if n not in common_words]
        claims.extend(names)
        
        return claims
    
    def _verify_claim(self, claim: str, source_data: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """Verify a single claim against source data"""
        
        # Convert source data to searchable text
        source_text = json.dumps(source_data, default=str).lower()
        claim_lower = claim.lower()
        
        # Check if claim appears in source data
        if claim_lower in source_text:
            return True, None
        
        # Check for numerical claims
        if '$' in claim or '%' in claim or 'score' in claim_lower:
            # Extract number from claim
            numbers = re.findall(r'\d+', claim)
            if numbers:
                number = numbers[0]
                if number in source_text:
                    return True, None
        
        # Claim not found in source
        issue = f"Unverified claim: '{claim}' not found in source data"
        return False, issue
    
    def _log_hallucination(self, query: str, response: str, results: Dict[str, Any]):
        """Log detected hallucination"""
        log_entry = {
            "timestamp": results["timestamp"],
            "query": query,
            "response": response[:200],  # Truncate
            "hallucination_score": results["hallucination_score"],
            "issues": results["issues"]
        }
        self.hallucination_log.append(log_entry)
    
    def get_hallucination_rate(self) -> float:
        """Calculate overall hallucination rate"""
        if not self.hallucination_log:
            return 0.0
        return len(self.hallucination_log) / max(len(self.hallucination_log), 1)
    
    def get_hallucination_report(self) -> Dict[str, Any]:
        """Generate hallucination report"""
        return {
            "total_evaluations": len(self.hallucination_log),
            "hallucinations_detected": len(self.hallucination_log),
            "hallucination_rate": self.get_hallucination_rate(),
            "recent_issues": self.hallucination_log[-5:] if self.hallucination_log else []
        }


class RAGQualityMetrics:
    """Measures RAG retrieval quality and relevance"""
    
    def __init__(self):
        self.evaluation_log: List[Dict[str, Any]] = []
    
    def evaluate_retrieval(self, query: str, retrieved_docs: List[Dict[str, Any]], 
                          expected_docs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Evaluate RAG retrieval quality
        
        Args:
            query: User's search query
            retrieved_docs: Documents retrieved by RAG
            expected_docs: Expected/relevant documents (for testing)
            
        Returns:
            Dictionary with quality metrics
        """
        results = {
            "retrieval_count": len(retrieved_docs),
            "relevance_score": 0.0,  # 0-1, how relevant are results
            "diversity_score": 0.0,  # 0-1, how diverse are results
            "coverage_score": 0.0,  # 0-1, how well query is covered
            "precision": 0.0,  # If expected_docs provided
            "recall": 0.0,  # If expected_docs provided
            "f1_score": 0.0,
            "timestamp": datetime.now().isoformat()
        }
        
        if not retrieved_docs:
            return results
        
        # Calculate relevance score
        results["relevance_score"] = self._calculate_relevance(query, retrieved_docs)
        
        # Calculate diversity score
        results["diversity_score"] = self._calculate_diversity(retrieved_docs)
        
        # Calculate coverage score
        results["coverage_score"] = self._calculate_coverage(query, retrieved_docs)
        
        # Calculate precision/recall if expected docs provided
        if expected_docs:
            precision, recall, f1 = self._calculate_precision_recall(
                retrieved_docs, expected_docs
            )
            results["precision"] = precision
            results["recall"] = recall
            results["f1_score"] = f1
        
        # Log evaluation
        self._log_evaluation(query, results)
        
        return results
    
    def _calculate_relevance(self, query: str, docs: List[Dict[str, Any]]) -> float:
        """Calculate average relevance of retrieved documents"""
        if not docs:
            return 0.0
        
        query_terms = set(query.lower().split())
        relevance_scores = []
        
        for doc in docs:
            # Get document text
            doc_text = doc.get('document', '')
            if not doc_text:
                doc_text = json.dumps(doc.get('metadata', {}))
            
            doc_terms = set(doc_text.lower().split())
            
            # Calculate term overlap
            overlap = len(query_terms & doc_terms)
            relevance = overlap / len(query_terms) if query_terms else 0
            relevance_scores.append(relevance)
        
        return sum(relevance_scores) / len(relevance_scores)
    
    def _calculate_diversity(self, docs: List[Dict[str, Any]]) -> float:
        """Calculate diversity of retrieved documents"""
        if len(docs) < 2:
            return 1.0
        
        # Check metadata diversity
        unique_types = set()
        unique_stages = set()
        unique_names = set()
        
        for doc in docs:
            metadata = doc.get('metadata', {})
            unique_types.add(metadata.get('type', ''))
            unique_stages.add(metadata.get('stage', ''))
            unique_names.add(metadata.get('name', ''))
        
        # Diversity = unique values / total docs
        diversity_scores = [
            len(unique_types) / len(docs),
            len(unique_stages) / len(docs),
            len(unique_names) / len(docs)
        ]
        
        return sum(diversity_scores) / len(diversity_scores)
    
    def _calculate_coverage(self, query: str, docs: List[Dict[str, Any]]) -> float:
        """Calculate how well documents cover the query"""
        if not docs:
            return 0.0
        
        query_terms = set(query.lower().split())
        covered_terms = set()
        
        for doc in docs:
            doc_text = doc.get('document', '')
            if not doc_text:
                doc_text = json.dumps(doc.get('metadata', {}))
            
            doc_terms = set(doc_text.lower().split())
            covered_terms.update(query_terms & doc_terms)
        
        return len(covered_terms) / len(query_terms) if query_terms else 0
    
    def _calculate_precision_recall(self, retrieved: List[Dict[str, Any]], 
                                   expected: List[Dict[str, Any]]) -> Tuple[float, float, float]:
        """Calculate precision, recall, and F1 score"""
        if not retrieved or not expected:
            return 0.0, 0.0, 0.0
        
        # Extract IDs from documents
        retrieved_ids = set(doc.get('id', str(i)) for i, doc in enumerate(retrieved))
        expected_ids = set(doc.get('id', str(i)) for i, doc in enumerate(expected))
        
        # Calculate metrics
        true_positives = len(retrieved_ids & expected_ids)
        
        precision = true_positives / len(retrieved_ids) if retrieved_ids else 0
        recall = true_positives / len(expected_ids) if expected_ids else 0
        
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return precision, recall, f1
    
    def _log_evaluation(self, query: str, results: Dict[str, Any]):
        """Log evaluation results"""
        log_entry = {
            "timestamp": results["timestamp"],
            "query": query,
            "metrics": {
                "relevance": results["relevance_score"],
                "diversity": results["diversity_score"],
                "coverage": results["coverage_score"]
            }
        }
        self.evaluation_log.append(log_entry)
    
    def get_average_metrics(self) -> Dict[str, float]:
        """Calculate average metrics across all evaluations"""
        if not self.evaluation_log:
            return {
                "avg_relevance": 0.0,
                "avg_diversity": 0.0,
                "avg_coverage": 0.0
            }
        
        total_relevance = sum(e["metrics"]["relevance"] for e in self.evaluation_log)
        total_diversity = sum(e["metrics"]["diversity"] for e in self.evaluation_log)
        total_coverage = sum(e["metrics"]["coverage"] for e in self.evaluation_log)
        
        count = len(self.evaluation_log)
        
        return {
            "avg_relevance": total_relevance / count,
            "avg_diversity": total_diversity / count,
            "avg_coverage": total_coverage / count,
            "total_evaluations": count
        }
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        avg_metrics = self.get_average_metrics()
        
        # Calculate quality grade
        overall_score = (
            avg_metrics["avg_relevance"] * 0.5 +
            avg_metrics["avg_diversity"] * 0.25 +
            avg_metrics["avg_coverage"] * 0.25
        )
        
        if overall_score >= 0.8:
            grade = "Excellent"
        elif overall_score >= 0.6:
            grade = "Good"
        elif overall_score >= 0.4:
            grade = "Fair"
        else:
            grade = "Poor"
        
        return {
            "overall_score": overall_score,
            "grade": grade,
            "metrics": avg_metrics,
            "recent_evaluations": self.evaluation_log[-5:] if self.evaluation_log else []
        }


class EvaluationManager:
    """Manages both hallucination detection and RAG quality evaluation"""
    
    def __init__(self):
        self.hallucination_detector = HallucinationDetector()
        self.rag_metrics = RAGQualityMetrics()
    
    def evaluate_response(self, query: str, response: str, 
                         source_data: List[Dict[str, Any]],
                         retrieved_docs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Comprehensive evaluation of AI response
        
        Args:
            query: User's query
            response: AI-generated response
            source_data: Original Salesforce data
            retrieved_docs: RAG retrieved documents (if RAG used)
            
        Returns:
            Complete evaluation results
        """
        results = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "hallucination_check": {},
            "rag_quality": {},
            "overall_quality": "Unknown"
        }
        
        # Check for hallucinations
        hallucination_results = self.hallucination_detector.detect_hallucinations(
            response, source_data, query
        )
        results["hallucination_check"] = hallucination_results
        
        # Evaluate RAG quality if retrieved docs provided
        if retrieved_docs:
            rag_results = self.rag_metrics.evaluate_retrieval(query, retrieved_docs)
            results["rag_quality"] = rag_results
        
        # Determine overall quality
        results["overall_quality"] = self._determine_quality(
            hallucination_results, 
            results.get("rag_quality", {})
        )
        
        return results
    
    def _determine_quality(self, hallucination_results: Dict[str, Any], 
                          rag_results: Dict[str, Any]) -> str:
        """Determine overall response quality"""
        
        # Check hallucination
        if hallucination_results.get("has_hallucination", False):
            return "Poor - Hallucinations Detected"
        
        # Check confidence
        confidence = hallucination_results.get("confidence", 0)
        
        if rag_results:
            relevance = rag_results.get("relevance_score", 0)
            
            if confidence >= 0.8 and relevance >= 0.7:
                return "Excellent"
            elif confidence >= 0.6 and relevance >= 0.5:
                return "Good"
            elif confidence >= 0.4:
                return "Fair"
            else:
                return "Poor"
        else:
            if confidence >= 0.8:
                return "Excellent"
            elif confidence >= 0.6:
                return "Good"
            elif confidence >= 0.4:
                return "Fair"
            else:
                return "Poor"
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive evaluation report"""
        return {
            "hallucination_report": self.hallucination_detector.get_hallucination_report(),
            "rag_quality_report": self.rag_metrics.get_quality_report(),
            "timestamp": datetime.now().isoformat()
        }
    
    def export_metrics(self, filepath: str):
        """Export evaluation metrics to JSON file"""
        report = self.get_comprehensive_report()
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filepath


# Usage example
def example_usage():
    """Example of using evaluation framework"""
    
    # Initialize
    evaluator = EvaluationManager()
    
    # Example data
    query = "Show me top leads"
    response = "Top 3 leads: John Doe (Acme Corp) - Score 85, Jane Smith (TechStart) - Score 78"
    source_data = [
        {"Name": "John Doe", "Company": "Acme Corp", "priority_score": 85},
        {"Name": "Jane Smith", "Company": "TechStart", "priority_score": 78}
    ]
    
    # Evaluate
    results = evaluator.evaluate_response(query, response, source_data)
    
    print("Evaluation Results:")
    print(f"Overall Quality: {results['overall_quality']}")
    print(f"Hallucination Score: {results['hallucination_check']['hallucination_score']:.2f}")
    print(f"Confidence: {results['hallucination_check']['confidence']:.2f}")
    
    # Get comprehensive report
    report = evaluator.get_comprehensive_report()
    print(f"\nHallucination Rate: {report['hallucination_report']['hallucination_rate']:.2%}")


if __name__ == "__main__":
    example_usage()
