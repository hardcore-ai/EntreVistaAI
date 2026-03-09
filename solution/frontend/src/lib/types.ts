export interface Campaign {
  id: string;
  title: string;
  role_description: string;
  requirements: Record<string, any>[];
  telegram_link_token: string;
  status: "active" | "paused" | "closed";
  retention_days: number | null;
  created_at: string;
  stats: {
    total: number;
    completed: number;
    abandoned: number;
    pending_review: number;
    completion_rate: number;
  };
}

export interface Evaluation {
  id: string;
  session_id: string;
  overall_score: number | null;
  ai_recommendation: "highly_recommended" | "recommended" | "needs_review" | "not_recommended" | null;
  summary: string;
  strengths: string[];
  concerns: string[];
  competency_scores: CompetencyScore[];
  status: "pending_review" | "approved" | "rejected" | "escalated";
  reviewed_by: string | null;
  reviewed_at: string | null;
  human_decision: string | null;
  human_notes: string | null;
  human_disagrees: boolean;
  created_at: string;
  candidate_name: string | null;
  session_status: string | null;
  campaign_title: string | null;
  conversation_history: Message[];
}

export interface CompetencyScore {
  competency: string;
  score: number;
  weight: number;
  rationale: string;
  quotes: string[];
}

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface Candidate {
  id: string;
  campaign_id: string;
  campaign_title: string | null;
  status: string;
  candidate_name: string | null;
  started_at: string;
  completed_at: string | null;
  current_question_index: number;
  has_evaluation: boolean;
  overall_score: number | null;
  ai_recommendation: string | null;
}
