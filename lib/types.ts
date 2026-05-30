export type FinanceType = "revenus" | "charges" | "epargne" | "dettes";

export type FinanceEntry = {
  id: number;
  type?: FinanceType | string;
  name?: string;
  label?: string;
  amount?: number | string;
};

export type FinancePayload = {
  type: FinanceType;
  name: string;
  amount: number;
};

export type FinanceData = Record<FinanceType, FinanceEntry[]>;

export type ChildAccount = {
  id: number;
  child_name: string;
  goal?: string | null;
  target_amount?: number | string;
  current_amount?: number | string;
  monthly_contribution?: number | string;
  horizon?: string | null;
  notes?: string | null;
  progress_percent?: number | string;
};

export type ChildAccountsData = {
  plan?: string;
  accounts?: ChildAccount[];
  totals?: {
    target_amount?: number | string;
    current_amount?: number | string;
    monthly_contribution?: number | string;
  };
};

export type PortfolioAsset = {
  id: number;
  asset_name?: string;
  name?: string;
  asset_type?: string;
  category?: string;
  type?: string;
  quantity?: number | string;
  purchase_price?: number | string;
  current_price?: number | string;
  value?: number | string;
  current_value?: number | string;
  cost?: number | string;
  gain?: number | string;
  pnl?: number | string;
  gain_percent?: number | string;
  pair_name?: string;
  currency_base?: string;
  currency_quote?: string;
  ticker?: string;
  source?: string;
};

export type PortfolioPayload = {
  asset_name: string;
  asset_type: string;
  quantity: number;
  purchase_price: number;
};

export type ProductModule = {
  key: string;
  label: string;
  stage: number;
  description?: string;
  state?: "active" | "locked" | string;
  required_plan?: string;
  required_score?: number;
  reason?: string;
};

export type ProductMission = {
  key: string;
  title: string;
  description: string;
  xp?: number;
  module?: string;
  recommended_plan?: string;
  validation?: string;
  context_reason?: string;
  completed?: boolean;
  status?: "pending" | "completed" | "verified" | string;
};

export type ProductSignal = {
  title?: string;
  description?: string;
  action?: string;
  status?: string;
  confidence?: string;
  xp?: number;
};

export type ProductBenchmarkDelta = {
  previous_value?: number;
  delta_value?: number;
  delta_percent?: number;
};

export type ProductOpportunityRadarItem = {
  key?: string;
  title?: string;
  why_fit?: string;
  time_fit?: string;
  impact?: string;
  next_action?: string;
  priority?: string;
};

export type ProductDependencySignal = {
  type?: string;
  title?: string;
  description?: string;
  severity?: string;
};

export type ProductContext = {
  plan?: string;
  next_plan?: string | null;
  score?: number;
  founder?: {
    is_founder?: boolean;
    tier?: string | null;
    discount?: number;
  };
  entitlements?: {
    plan?: string;
    max_assets?: number | null;
    ai_level?: string;
    modules?: string[];
    features?: string[];
    copy?: {
      name?: string;
      price?: string;
      promise?: string;
    };
  };
  progression?: {
    xp?: number;
    streak?: number;
    level?: string;
    status?: string;
    next_level_xp?: number;
    progress_percent?: number;
  };
  data_profile?: {
    finance_count?: number;
    portfolio_count?: number;
    real_estate_count?: number;
    yield_count?: number;
    venture_count?: number;
    total_assets_count?: number;
    completed_steps?: number;
    completion_percent?: number;
    monthly_income?: number;
    monthly_expenses?: number;
    monthly_savings?: number;
    monthly_capacity?: number;
    debt_total?: number;
    portfolio_value?: number;
    real_estate_value?: number;
    yield_value?: number;
    venture_value?: number;
    business_value?: number;
    current_wealth?: number;
  };
  life_profile?: {
    goals?: string[];
    professional_context?: string | null;
    motivation?: string | null;
    has_children?: boolean;
    transmission_goal?: string | null;
    governance_need?: string | null;
  };
  modules?: {
    visible?: ProductModule[];
    locked?: ProductModule[];
  };
  missions?: ProductMission[];
  strategic_brief?: {
    priority?: string;
    main_lever?: string;
    main_risk?: string;
    opportunity?: string;
    next_action?: string;
    context_basis?: {
      goals?: string[];
      has_children?: boolean;
      professional_context?: string | null;
    };
  };
  mission_control?: {
    risk?: ProductSignal;
    opportunity?: ProductSignal;
    decision?: ProductSignal;
    mission?: ProductSignal;
    future_signal?: ProductSignal;
  };
  future_view?: {
    title?: string;
    current_wealth?: number;
    monthly_capacity?: number;
    annual_return?: number;
    confidence?: string;
    assumption?: string;
    scenarios?: Array<{
      label?: string;
      years?: number;
      value?: number;
    }>;
  };
  wealth_timeline?: {
    current_wealth?: number;
    progress_percent?: number;
    next_milestone?: {
      label?: string;
      target?: number;
    } | null;
    stages?: Array<{
      label?: string;
      target?: number;
      status?: string;
      progress_percent?: number;
    }>;
  };
  family_office_view?: {
    title?: string;
    summary?: string;
    global_wealth?: number;
    active_domains?: number;
    plan?: string;
    allocation?: Array<{
      key?: string;
      label?: string;
      value?: number;
      description?: string;
    }>;
  };
  wealth_gps?: {
    title?: string;
    current_position?: number;
    next_destination?: number;
    assumption?: string;
    routes?: Array<{
      key?: string;
      label?: string;
      annual_return?: number;
      monthly_multiplier?: number;
      value_10y?: number;
      years_to_next_milestone?: number | null;
      description?: string;
    }>;
  };
  digital_twin?: {
    title?: string;
    basis?: string;
    scenarios?: Array<{
      key?: string;
      label?: string;
      monthly_delta?: number;
      annual_return?: number;
      value_5y?: number;
      value_10y?: number;
      description?: string;
    }>;
  };
  weak_signals?: {
    title?: string;
    signals?: Array<{
      type?: string;
      title?: string;
      description?: string;
      severity?: string;
    }>;
  };
  self_benchmark?: {
    title?: string;
    current_wealth?: number;
    six_months?: ProductBenchmarkDelta | null;
    twelve_months?: ProductBenchmarkDelta | null;
    basis?: string;
  };
  wealth_story?: {
    title?: string;
    events?: Array<{
      label?: string;
      title?: string;
      description?: string;
    }>;
  };
  opportunity_radar?: {
    title?: string;
    principle?: string;
    items?: ProductOpportunityRadarItem[];
  };
  decision_engine?: {
    title?: string;
    decisions?: Array<{
      key?: string;
      label?: string;
      cashflow?: string;
      liquidity?: string;
      risk?: string;
      freedom_impact?: string;
      fit?: string;
      comment?: string;
    }>;
  };
  time_value?: {
    title?: string;
    hourly_value?: number;
    monthly_capacity?: number;
    basis?: string;
    levers?: Array<{
      label?: string;
      time_cost?: string;
      leverage?: string;
      reading?: string;
    }>;
  };
  wealth_blocks?: {
    title?: string;
    blocks?: Array<{
      key?: string;
      label?: string;
      value?: number;
      status?: string;
      description?: string;
    }>;
  };
  dependency_detector?: {
    title?: string;
    signals?: ProductDependencySignal[];
  };
  personal_command_center?: {
    title?: string;
    situation?: string;
    threat?: ProductDependencySignal | null;
    opportunity?: ProductOpportunityRadarItem | ProductSignal | null;
    mission?: ProductSignal | null;
    next_step?: string;
    time_value?: ProductContext["time_value"];
  };
};

export type LegacyOverview = {
  counts?: {
    family_vault?: number;
    heirs?: number;
    governance_rules?: number;
  };
  scores?: {
    legacy_score?: number;
    dynasty_stability_score?: number;
    transmission_readiness?: number;
    family_governance_index?: number;
    asset_protection_index?: number;
  };
  insights?: string[];
  modules?: string[];
};

export type RealEstateType = "primary_residence" | "flip" | "rental";

export type RealEstateAsset = {
  id: number;
  property_type: RealEstateType;
  name: string;
  purchase_price?: number | string;
  estimated_value?: number | string;
  resale_price?: number | string;
  monthly_rent?: number | string;
  monthly_charges?: number | string;
  target_value?: number | string;
  potential_gain?: number | string;
  potential_gain_percent?: number | string;
  annual_net_rent?: number | string;
  rental_yield?: number | string;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type RealEstatePayload = {
  property_type: RealEstateType;
  name: string;
  purchase_price: number;
  estimated_value: number;
  resale_price: number;
  monthly_rent: number;
  monthly_charges: number;
  notes?: string | null;
};

export type RealEstateData = {
  assets: RealEstateAsset[];
  totals: {
    total_purchase?: number | string;
    total_estimated_value?: number | string;
    total_potential_gain?: number | string;
    total_potential_gain_percent?: number | string;
    average_rental_yield?: number | string;
  };
};

export type YieldAssetType = "crowdfunding" | "private_equity";

export type YieldAsset = {
  id: number;
  asset_type: YieldAssetType;
  name: string;
  principal?: number | string;
  average_rate?: number | string;
  duration_months?: number | string;
  projected_gain?: number | string;
  final_value?: number | string;
  notes?: string | null;
};

export type YieldAssetPayload = {
  asset_type: YieldAssetType;
  name: string;
  principal: number;
  average_rate: number;
  duration_months: number;
  notes?: string | null;
};

export type YieldAssetData = {
  assets: YieldAsset[];
  totals: {
    total_principal?: number | string;
    total_projected_gain?: number | string;
    total_final_value?: number | string;
    average_rate?: number | string;
  };
};

export type VentureAssetType = "ai_business" | "business" | "startup" | "franchise";

export type VentureAsset = {
  id: number;
  asset_type: VentureAssetType;
  name: string;
  revenue?: number | string;
  charges?: number | string;
  result?: number | string;
  fundraising?: number | string;
  debts?: number | string;
  valuation?: number | string;
  computed_value?: number | string;
  final_value?: number | string;
  notes?: string | null;
};

export type VentureAssetPayload = {
  asset_type: VentureAssetType;
  name: string;
  revenue: number;
  charges: number;
  fundraising: number;
  debts: number;
  valuation: number;
  notes?: string | null;
};

export type VentureAssetData = {
  assets: VentureAsset[];
  totals: {
    total_revenue?: number | string;
    total_charges?: number | string;
    total_result?: number | string;
    total_fundraising?: number | string;
    total_debts?: number | string;
    total_final_value?: number | string;
  };
};

export type Opportunity = {
  type?: string;
  title?: string;
  description?: string;
  priority?: "high" | "medium" | "low" | string;
  score?: number;
  premium?: boolean;
  why_this_opportunity?: string;
  why_now?: string;
  impact_potential?: string;
  difficulty?: string;
  profile_compatibility?: string;
  next_action?: string;
};

export type OpportunityData = {
  count?: number;
  opportunities?: Opportunity[];
  analytics?: {
    crypto_ratio?: number;
    asset_types_count?: number;
    portfolio_value?: number;
  };
};

export type UserIntelligence = {
  global_score?: number;
  level?: string;
  opportunities?: OpportunityData | Opportunity[];
  strategic_intelligence?: Record<string, unknown>;
  financial_features?: Record<string, unknown>;
};

export type CategoryOpportunity = {
  key?: string;
  title?: string;
  count?: number;
  analysis?: string;
  quick_action?: string;
  detected_opportunity?: {
    title?: string;
    type?: string;
    risk?: string;
    potential?: string;
    platform?: string;
  } | null;
  market_signal?: {
    query?: string;
    sentiment?: string;
    sentiment_score?: number;
    headline?: string | null;
    source?: string | null;
  };
};

export type CategoryOpportunityData = {
  categories?: CategoryOpportunity[];
};

export type OpportunityUniverse = "real_estate" | "investments" | "business";

export type OpportunityIntelligenceItem = {
  id?: string;
  universe?: OpportunityUniverse;
  type?: string;
  title?: string;
  description?: string;
  source?: string;
  url?: string | null;
  link_or_source?: string | null;
  image_url?: string | null;
  location?: string;
  expected_return?: string;
  risk_level?: string;
  investment_horizon?: string;
  strategy_type?: string;
  score?: {
    final_score?: number;
    breakdown?: {
      return_score?: number;
      risk_score?: number;
      liquidity_score?: number;
      diversification_score?: number;
      portfolio_fit_score?: number;
      momentum_score?: number;
      novelty_score?: number;
    };
  };
  budget?: string | number | null;
  price?: string | number | null;
  yield_percent?: string | number | null;
  cashflow_estimate?: string | number | null;
  volatility?: string | null;
  momentum?: string | null;
  ethan_score?: string | number | null;
  strengths?: string[];
  risks?: string[];
  projection?: string;
  next_step?: string;
  explanation?: string;
  why_this_is_new_vs_previous?: string;
};

export type OpportunityIntelligenceData = {
  version?: string;
  data_hash?: string;
  timestamp?: string;
  universe?: OpportunityUniverse;
  plan?: string;
  depth?: {
    max_results?: number;
    depth?: string;
    advanced?: boolean;
    message?: string;
  };
  items?: OpportunityIntelligenceItem[];
  sources?: string[];
  market_signal?: {
    query?: string;
    sentiment?: string;
    sentiment_score?: number;
    headline?: string | null;
    source?: string | null;
  };
  generated_at?: string;
  cache_hit?: boolean;
};

export type PortfolioHistoryPoint = {
  date?: string;
  created_at?: string;
  value?: number | string;
  cost?: number | string;
  gain?: number | string;
};

export type ScoreDetails = {
  wealth?: number;
  diversification?: number;
  debt?: number;
  debt_risk_score?: number;
  activity?: number;
};

export type CommandCenter = {
  version?: string;
  data_hash?: string;
  timestamp?: string;
  global_score?: number;
  level?: string;
  family_office_score?: {
    details?: ScoreDetails;
  };
  advice?: string[];
  module_signals?: Array<{
    module?: string;
    domain?: string;
    signal?: string;
    severity?: string;
    label?: string;
  }>;
  opportunities?: OpportunityData | Opportunity[];
  opportunities_count?: number;
  modules?: Record<string, { score?: number }>;
  onboarding?: OnboardingData;
};

export type OnboardingData = {
  revenus_mensuels?: number;
  charges_mensuelles?: number;
  monthly_income?: number;
  monthly_expenses?: number;
  profile_completed?: boolean;
};

export type UserProfile = OnboardingData & {
  id?: number;
  email?: string;
  plan?: string;
  level?: string;
  is_founder?: boolean;
  founder_tier?: string | null;
  founder_discount?: number;
};

export type GamificationData = {
  version?: string;
  data_hash?: string;
  timestamp?: string;
  xp?: number;
  xp_to_next_level?: number;
  progress_xp?: number;
  progress_percent?: number;
  level?: number | string;
  streak?: number;
  badges?: string[];
  ai_coach?: {
    message?: string;
    affiliations?: Array<{
      title?: string;
      reason?: string;
      priority?: string;
    }>;
  };
  reward?: { title?: string; description?: string };
  notification?: { title?: string; message?: string };
  actions?: Array<{
    title?: string;
    description?: string;
    xp?: number;
  }>;
  upgrade?: {
    recommended_plan?: string;
    title?: string;
    description?: string;
  };
};

export type DashboardSummary = {
  plan?: string;
  level?: string;
  next_plan?: string | null;
  is_founder?: boolean;
  founder_tier?: string | null;
  founder_discount?: number;
};

export type WorkspaceMember = {
  email?: string;
  role?: "owner" | "admin" | "member" | "viewer" | string;
  status?: string;
  created_at?: string | null;
};

export type Workspace = {
  id: number;
  name?: string;
  plan?: string;
  role?: "owner" | "admin" | "member" | "viewer" | string;
  owner_user_id?: number;
  members?: WorkspaceMember[];
};

export type WorkspaceData = {
  active_workspace_id?: number;
  workspaces?: Workspace[];
};
