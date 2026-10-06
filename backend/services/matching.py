from sqlalchemy.orm import Session
from models import User, Project, Milestone
from services.ledger_service import ledger_service

class MatchingService:
    @staticmethod
    def match_team(db: Session, project_id: int) -> dict:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"experts": [], "students": [], "filtered_out": []}

        sponsor = project.sponsor
        sponsor_org = sponsor.institution if sponsor and sponsor.institution else ""

        # Collect project required skills from milestones or default
        milestones = db.query(Milestone).filter(Milestone.project_id == project_id).all()
        project_skills = set()
        for m in milestones:
            if m.skills_required:
                project_skills.update(m.skills_required)
        if not project_skills:
            project_skills = {"PyTorch", "Medical Imaging", "Edge Deployment", "Benchmarking"}

        users = db.query(User).all()

        experts = []
        students = []
        filtered_out = []

        for user in users:
            if user.id == project.sponsor_id:
                continue

            user_skills = set(user.skills or [])
            overlapping_skills = list(project_skills.intersection(user_skills))
            score = len(overlapping_skills)

            reason = f"matches {len(overlapping_skills)}/{len(project_skills)} skills: {', '.join(overlapping_skills) if overlapping_skills else 'General'}; {user.verification_level} verified"

            if user.role == "EXPERT":
                # COI check
                has_coi = False
                for conflict in (user.conflicts or []):
                    if conflict.lower() in sponsor_org.lower() or (sponsor_org and sponsor_org.lower() in conflict.lower()):
                        has_coi = True
                        coi_reason = f"Filtered out: conflict of interest with {conflict}"
                        filtered_out.append({
                            "user_id": user.id,
                            "name": user.name,
                            "role": user.role,
                            "reason": coi_reason
                        })
                        ledger_service.append(
                            db=db,
                            actor_type="system",
                            actor_id=0,
                            project_id=project_id,
                            action="COI_FILTERED",
                            decision="BLOCK",
                            reason=f"Expert {user.name} ({user.id}) filtered out due to COI with {conflict}"
                        )
                        break

                if not has_coi:
                    experts.append({
                        "user_id": user.id,
                        "name": user.name,
                        "role": user.role,
                        "score": score,
                        "verification_level": user.verification_level,
                        "reason": reason
                    })

            elif user.role == "STUDENT":
                students.append({
                    "user_id": user.id,
                    "name": user.name,
                    "role": user.role,
                    "score": score,
                    "verification_level": user.verification_level,
                    "reason": reason
                })

        # Rank by score desc
        experts.sort(key=lambda x: x["score"], reverse=True)
        students.sort(key=lambda x: x["score"], reverse=True)

        selected_expert = experts[:1]
        selected_students = students[:3]

        ledger_service.append(
            db=db,
            actor_type="system",
            actor_id=0,
            project_id=project_id,
            action="MATCH_COMPUTED",
            reason=f"Computed matches for project {project_id}: 1 expert, {len(selected_students)} students selected"
        )

        return {
            "experts": selected_expert,
            "students": selected_students,
            "filtered_out": filtered_out
        }

matching_service = MatchingService()
