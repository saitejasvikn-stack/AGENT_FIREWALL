import math
from typing import Dict, List, Any

class RewardEngine:
    @staticmethod
    def calculate_money_payout(
        milestone_budget: int,
        student_weights: Dict[int, float],  # {user_id: weight}
        fee_pct: float = 10.0,
        ai_reserve_pct: float = 5.0,
        expert_pct_of_remainder: float = 30.0,
        student_equal_pct: float = 40.0,
        expert_user_id: int | None = None
    ) -> Dict[str, Any]:
        M = milestone_budget
        fee = int(M * (fee_pct / 100.0))
        ai_reserve = int(M * (ai_reserve_pct / 100.0))
        remainder = M - fee - ai_reserve
        expert_share = int(remainder * (expert_pct_of_remainder / 100.0))
        student_pool = remainder - expert_share

        num_students = len(student_weights)
        if num_students == 0:
            return {
                "fee": fee,
                "ai_reserve": ai_reserve,
                "expert_share": expert_share,
                "student_payouts": {},
                "total": fee + ai_reserve + expert_share
            }

        equal_pool = student_pool * (student_equal_pct / 100.0)
        weighted_pool = student_pool * (1.0 - (student_equal_pct / 100.0))

        # Calculate exact float shares and integer floors
        raw_shares = {}
        floored_shares = {}
        remainders = {}

        for user_id, weight in student_weights.items():
            eq_part = equal_pool / num_students
            wt_part = weighted_pool * weight
            exact = eq_part + wt_part
            raw_shares[user_id] = exact
            floored = int(math.floor(exact))
            floored_shares[user_id] = floored
            remainders[user_id] = exact - floored

        allocated_students = sum(floored_shares.values())
        unallocated_rupees = student_pool - allocated_students

        # Sort by remainder descending, tie-break by lowest weight (or user_id asc)
        sorted_users = sorted(
            student_weights.keys(),
            key=lambda uid: (remainders[uid], -student_weights[uid]),
            reverse=True
        )

        final_student_payouts = dict(floored_shares)
        for i in range(unallocated_rupees):
            uid = sorted_users[i % len(sorted_users)]
            final_student_payouts[uid] += 1

        total_distributed = fee + ai_reserve + expert_share + sum(final_student_payouts.values())

        payout_explanations = {}
        for uid, amount in final_student_payouts.items():
            w = student_weights[uid]
            payout_explanations[uid] = {
                "milestone_budget": M,
                "fee": fee,
                "ai_reserve": ai_reserve,
                "expert_share": expert_share,
                "student_pool": student_pool,
                "weight": w,
                "equal_component": round(equal_pool / num_students, 2),
                "weighted_component": round(weighted_pool * w, 2),
                "final_amount_inr": amount,
                "ai_earned": 0
            }

        return {
            "fee": fee,
            "ai_reserve": ai_reserve,
            "expert_share": expert_share,
            "student_payouts": final_student_payouts,
            "explanations": payout_explanations,
            "total": total_distributed
        }

    @staticmethod
    def calculate_credit_payout(
        credit_pool_cu: float,
        student_weights: Dict[int, float],
        expert_pct: float = 20.0,
        student_equal_pct: float = 30.0
    ) -> Dict[str, Any]:
        expert_cu = credit_pool_cu * (expert_pct / 100.0)
        student_pool_cu = credit_pool_cu - expert_cu

        num_students = len(student_weights)
        if num_students == 0:
            return {
                "expert_cu": expert_cu,
                "student_payouts_cu": {},
                "total_cu": expert_cu
            }

        equal_pool_cu = student_pool_cu * (student_equal_pct / 100.0)
        weighted_pool_cu = student_pool_cu * (1.0 - (student_equal_pct / 100.0))

        student_payouts_cu = {}
        explanations = {}

        for user_id, weight in student_weights.items():
            eq_part = equal_pool_cu / num_students
            wt_part = weighted_pool_cu * weight
            total_cu = round(eq_part + wt_part, 2)
            student_payouts_cu[user_id] = total_cu

            explanations[user_id] = {
                "credit_pool_cu": credit_pool_cu,
                "expert_cu": expert_cu,
                "student_pool_cu": student_pool_cu,
                "weight": weight,
                "equal_component_cu": round(eq_part, 2),
                "weighted_component_cu": round(wt_part, 2),
                "final_credit_cu": total_cu,
                "ai_earned_cu": 0
            }

        total_cu_distributed = round(expert_cu + sum(student_payouts_cu.values()), 2)

        return {
            "expert_cu": round(expert_cu, 2),
            "student_payouts_cu": student_payouts_cu,
            "explanations": explanations,
            "total_cu": total_cu_distributed
        }

reward_engine = RewardEngine()
