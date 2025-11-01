"""Prompt building for LLM fine-tuning corpus."""

from typing import List, Optional

from src.models.issue import Issue, IssueComment


class PromptBuilder:
    """Build Alpaca-style prompts from Jira issues."""

    @staticmethod
    def build_instruction(issue: Issue) -> str:
        """Build instruction from issue summary, description, and task context.

        Args:
            issue: Jira issue

        Returns:
            Instruction string
        """
        parts = []

        # Summary
        if issue.fields.summary:
            parts.append(f"Title: {issue.fields.summary}")

        # Description
        if issue.fields.description:
            # Clean HTML/plain text description
            description = PromptBuilder._clean_text(issue.fields.description)
            parts.append(f"Description: {description}")

        # Task context (status, type, priority)
        task_parts = []
        if issue.fields.status:
            status_name = issue.fields.status.get("name", "")
            if status_name:
                task_parts.append(f"Status: {status_name}")

        if issue.fields.issue_type:
            type_name = issue.fields.issue_type.get("name", "")
            if type_name:
                task_parts.append(f"Type: {type_name}")

        if issue.fields.priority:
            priority_name = issue.fields.priority.get("name", "")
            if priority_name:
                task_parts.append(f"Priority: {priority_name}")

        if task_parts:
            parts.append(" | ".join(task_parts))

        # Build final instruction
        instruction = "\n\n".join(parts)
        if not instruction.strip():
            instruction = f"Issue: {issue.key}"

        return instruction

    @staticmethod
    def build_response(issue: Issue, comments: Optional[List[IssueComment]] = None) -> str:
        """Build response from resolution comments.

        Args:
            issue: Jira issue
            comments: Optional list of comments to use (defaults to issue.get_resolution_comments())

        Returns:
            Response string
        """
        if comments is None:
            comments = issue.get_resolution_comments()

        if not comments:
            # Fallback: use resolution info if available
            if issue.fields.resolution:
                resolution_name = issue.fields.resolution.get("name", "")
                if resolution_name and resolution_name.lower() != "unresolved":
                    return f"Resolution: {resolution_name}"
            return "No resolution information available."

        # Combine top resolution comments
        response_parts = []
        for i, comment in enumerate(comments[:3], 1):
            body = PromptBuilder._clean_text(comment.body)
            if body.strip():
                response_parts.append(body)

        if not response_parts:
            return "No resolution comments found."

        response = "\n\n---\n\n".join(response_parts)
        return response

    @staticmethod
    def build_alpaca_format(
        issue: Issue, instruction: Optional[str] = None, response: Optional[str] = None
    ) -> dict:
        """Build Alpaca-style format for LLM fine-tuning.

        Args:
            issue: Jira issue
            instruction: Optional instruction (defaults to build_instruction)
            response: Optional response (defaults to build_response)

        Returns:
            Dictionary with 'instruction' and 'response' keys
        """
        if instruction is None:
            instruction = PromptBuilder.build_instruction(issue)
        if response is None:
            response = PromptBuilder.build_response(issue)

        return {
            "instruction": instruction,
            "response": response,
            "input": "",  # Alpaca format has an optional 'input' field
        }

    @staticmethod
    def build_summarization_task(issue: Issue) -> dict:
        """Build summarization task: summarize issue description and comments.
        
        Args:
            issue: Jira issue
            
        Returns:
            Dictionary with summarization task
        """
        description = PromptBuilder._clean_text(issue.fields.description or "")
        comments_text = "\n\n".join([
            PromptBuilder._clean_text(c.body) 
            for c in issue.comments[:5]  # Top 5 comments
        ])
        
        input_text = f"{description}\n\nComments:\n{comments_text}".strip()
        
        # Use summary as the target summary, or create one from key fields
        summary_text = issue.fields.summary or f"Issue {issue.key}"
        if issue.fields.resolution:
            resolution = issue.fields.resolution.get("name", "")
            if resolution:
                summary_text += f" - Resolved: {resolution}"
        
        return {
            "task": "summarization",
            "input": input_text[:2000],  # Limit length
            "output": summary_text,
        }

    @staticmethod
    def build_classification_task(issue: Issue) -> dict:
        """Build classification task: classify issue type, priority, status.
        
        Args:
            issue: Jira issue
            
        Returns:
            Dictionary with classification task
        """
        description = PromptBuilder._clean_text(issue.fields.description or "")
        summary = issue.fields.summary or ""
        
        input_text = f"Title: {summary}\n\nDescription: {description}".strip()
        
        # Extract classification labels
        issue_type = issue.fields.issue_type.get("name", "") if issue.fields.issue_type else ""
        priority = issue.fields.priority.get("name", "") if issue.fields.priority else ""
        status = issue.fields.status.get("name", "") if issue.fields.status else ""
        resolution = issue.fields.resolution.get("name", "") if issue.fields.resolution else ""
        
        output_labels = []
        if issue_type:
            output_labels.append(f"Type: {issue_type}")
        if priority:
            output_labels.append(f"Priority: {priority}")
        if status:
            output_labels.append(f"Status: {status}")
        if resolution:
            output_labels.append(f"Resolution: {resolution}")
        
        output_text = " | ".join(output_labels) if output_labels else "Unclassified"
        
        return {
            "task": "classification",
            "input": input_text[:2000],
            "output": output_text,
        }

    @staticmethod
    def build_qa_task(issue: Issue) -> dict:
        """Build Q&A task: question about the issue with answer from comments/resolution.
        
        Args:
            issue: Jira issue
            
        Returns:
            Dictionary with Q&A task
        """
        summary = issue.fields.summary or f"Issue {issue.key}"
        description = PromptBuilder._clean_text(issue.fields.description or "")
        
        # Generate question from issue
        question = f"What is the issue with '{summary}' and how was it resolved?"
        
        # Build context from description
        context = f"Title: {summary}"
        if description:
            context += f"\n\nDescription: {description}"
        
        # Get answer from comments or resolution
        resolution_comments = issue.get_resolution_comments(limit=2)
        if resolution_comments:
            answer = "\n\n".join([
                PromptBuilder._clean_text(c.body) 
                for c in resolution_comments
            ])
        elif issue.fields.resolution:
            resolution_name = issue.fields.resolution.get("name", "")
            answer = f"The issue was resolved as: {resolution_name}"
        else:
            answer = "The issue status and resolution details are not available."
        
        return {
            "task": "qa",
            "question": question,
            "context": context[:2000],
            "answer": answer[:1000],
        }

    @staticmethod
    def build_all_tasks(issue: Issue) -> dict:
        """Build all derived tasks for an issue.
        
        Args:
            issue: Jira issue
            
        Returns:
            Dictionary containing all tasks (summarization, classification, qa) plus metadata
        """
        # Get full issue text
        description = PromptBuilder._clean_text(issue.fields.description or "")
        comments = [
            {
                "author": c.author.get("displayName", "Unknown") if isinstance(c.author, dict) else "Unknown",
                "body": PromptBuilder._clean_text(c.body),
                "created": c.created.isoformat() if hasattr(c.created, 'isoformat') else str(c.created),
            }
            for c in issue.comments
        ]
        
        # Build metadata
        metadata = {
            "issue_key": issue.key,
            "project": issue.project,
            "title": issue.fields.summary,
            "status": issue.fields.status.get("name", "") if issue.fields.status else "",
            "priority": issue.fields.priority.get("name", "") if issue.fields.priority else "",
            "reporter": issue.fields.reporter.get("displayName", "") if isinstance(issue.fields.reporter, dict) else "",
            "created": issue.fields.created.isoformat() if hasattr(issue.fields.created, 'isoformat') else str(issue.fields.created),
            "updated": issue.fields.updated.isoformat() if hasattr(issue.fields.updated, 'isoformat') else str(issue.fields.updated),
        }
        
        if issue.fields.assignee:
            metadata["assignee"] = issue.fields.assignee.get("displayName", "") if isinstance(issue.fields.assignee, dict) else ""
        
        if issue.fields.resolution:
            metadata["resolution"] = issue.fields.resolution.get("name", "")
        
        # Build all tasks
        return {
            "metadata": metadata,
            "description": description,
            "comments": comments,
            "tasks": {
                "summarization": PromptBuilder.build_summarization_task(issue),
                "classification": PromptBuilder.build_classification_task(issue),
                "qa": PromptBuilder.build_qa_task(issue),
            }
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean HTML and format text.

        Args:
            text: Raw text (may contain HTML)

        Returns:
            Cleaned plain text
        """
        if not text:
            return ""

        import re

        # Remove HTML tags (basic)
        text = re.sub(r"<[^>]+>", "", text)
        # Decode HTML entities
        import html

        text = html.unescape(text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

