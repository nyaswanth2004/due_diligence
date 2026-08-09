"""Risk agent: flags red flags and anomalies with evidence."""

from dataclasses import dataclass, field

from app.analysis.agents.base import Agent, AgentContext, AgentResult

RED_FLAG_PATTERNS: list[tuple[str, str]] = [
    (r"\blitigation\b", "Litigation is mentioned."),
    (r"\bgoing\s+concern\b", "Going-concern doubt is raised."),
    (r"\brelated\s+party\b", "Related-party transactions are disclosed."),
    (r"\bimpairment\b", "Asset impairment is recognized."),
    (r"\brestatement\b", "A financial restatement is disclosed."),
    (r"\bmaterial\s+weakness\b", "A material weakness in controls is reported."),
    (r"\bdefault\b", "A default or potential default is mentioned."),
    (r"\bcontingent\s+liabilit", "Contingent liabilities are disclosed."),
    (r"\bgoing\s+concern\s+qualification", "Going-concern qualification present."),
]


@dataclass
class RedFlag:
    severity: str
    finding: str
    evidence: str
    chunk_id: str = ""
    page: int = 0


@dataclass
class RiskData:
    red_flags: list[RedFlag]
    source_chunk_ids: list[str] = field(default_factory=list)


class RiskAgent(Agent):
    """Scans all chunks for language consistent with financial risk."""

    name = "risk"

    def run(self, context: AgentContext) -> AgentResult:
        import re

        flags: list[RedFlag] = []
        seen: set[tuple[str, str]] = set()
        for chunk in context.chunks:
            text = chunk.content.lower()
            for pattern, finding in RED_FLAG_PATTERNS:
                if re.search(pattern, text) and (pattern, finding) not in seen:
                    seen.add((pattern, finding))
                    flags.append(RedFlag(
                        severity="high",
                        finding=finding,
                        evidence=chunk.content[:220],
                        chunk_id=chunk.id,
                        page=chunk.page_number,
                    ))

        # Numeric red flags from ratios.
        if context.ratios:
            for ratio in context.ratios:
                if ratio.risk_level == "high":
                    flags.append(RedFlag(
                        severity="high",
                        finding=f"{ratio.name} is outside the safe range ({ratio.interpretation}).",
                        evidence=f"Value: {ratio.value}; {ratio.formula}",
                        chunk_id=ratio.source_chunk_ids[0] if ratio.source_chunk_ids else "",
                    ))
            # Flag loss-making years via negative net income trends.
            if context.financials:
                ni = context.financials.first("net_income")
                if ni and ni.value < 0:
                    flags.append(RedFlag(
                        severity="high",
                        finding="The company reports a net loss for the period.",
                        evidence=f"Net income of {ni.value}.",
                        chunk_id=ni.chunk_id,
                        page=ni.page,
                    ))

        deduped: list[RedFlag] = []
        seen_findings: set[str] = set()
        for flag in flags:
            if flag.finding not in seen_findings:
                seen_findings.add(flag.finding)
                deduped.append(flag)

        data = RiskData(
            red_flags=deduped,
            source_chunk_ids=sorted({f.chunk_id for f in deduped if f.chunk_id}),
        )
        return AgentResult(agent=self.name, data=data, citations=data.source_chunk_ids)
