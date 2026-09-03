from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..missions.registry import list_missions
from ..store.progress_store import get_progress


def register_get_student_analytics(server: MCPServer) -> None:
    @server.tool(
        name="get_student_analytics",
        description=(
            "Retrieves a comprehensive learning and mastery report for a student. "
            "Includes total missions attempted, completion rate, accuracy, and "
            "recommended next missions. Use this to personalize tutoring, track "
            "growth, and celebrate milestones."
        ),
    )
    def get_student_analytics(studentId: str) -> CallToolResult:
        """
        Args:
            studentId: The stable identifier for the student.
        """
        all_missions = list_missions()
        total_available = len(all_missions)
        records = get_progress(studentId)

        record_map = {r["missionId"]: r for r in records}

        completed_count = 0
        total_attempts = 0
        mission_breakdown = []
        uncompleted_missions = []

        for m in all_missions:
            rec = record_map.get(m.id)
            if rec:
                attempts = rec.get("attempts", 0)
                completed_at = rec.get("completedAt", "")
                is_completed = bool(completed_at)
                total_attempts += attempts
                if is_completed:
                    completed_count += 1
                else:
                    uncompleted_missions.append(m)

                mission_breakdown.append({
                    "missionId": m.id,
                    "title": m.title,
                    "type": m.type,
                    "concept": m.concept,
                    "status": "COMPLETED" if is_completed else "IN_PROGRESS",
                    "attempts": attempts,
                    "completedAt": completed_at,
                })
            else:
                uncompleted_missions.append(m)
                mission_breakdown.append({
                    "missionId": m.id,
                    "title": m.title,
                    "type": m.type,
                    "concept": m.concept,
                    "status": "NOT_STARTED",
                    "attempts": 0,
                    "completedAt": "",
                })

        completion_pct = round((completed_count / total_available * 100), 1) if total_available > 0 else 0.0
        success_rate = round((completed_count / total_attempts * 100), 1) if total_attempts > 0 else 0.0

        if uncompleted_missions:
            next_mission = uncompleted_missions[0]
            recommendation = f"Recommended next mission: '{next_mission.title}' (concept: {next_mission.concept})."
        else:
            recommendation = "All available missions completed! Excellent work mastering these foundational concepts."

        summary_lines = [
            f"📊 Learning Analytics for Student '{studentId}':",
            f"• Missions Completed: {completed_count} / {total_available} ({completion_pct}%)",
            f"• Total Attempts: {total_attempts}",
            f"• Mastery Rate: {success_rate}%",
            f"• {recommendation}",
            "\nMission Breakdown:",
        ]

        for mb in mission_breakdown:
            status_icon = "✓" if mb["status"] == "COMPLETED" else ("⏳" if mb["status"] == "IN_PROGRESS" else "○")
            summary_lines.append(f"  {status_icon} [{mb['status']}] {mb['title']} ({mb['attempts']} attempts)")

        return CallToolResult(
            content=[TextContent(type="text", text="\n".join(summary_lines))],
            structured_content={
                "studentId": studentId,
                "totalAvailable": total_available,
                "completedCount": completed_count,
                "completionPercentage": completion_pct,
                "totalAttempts": total_attempts,
                "successRate": success_rate,
                "recommendation": recommendation,
                "missions": mission_breakdown,
            },
            is_error=False,
        )
