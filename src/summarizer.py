import shutil
import subprocess
import sys
from dataclasses import dataclass

from .formatter import group_news_by_section


@dataclass
class SummaryResult:
    summary: str
    prompt_path: object
    output_path: object


def _format_news_for_prompt(news_items):
    lines = []
    for section, items in group_news_by_section(news_items):
        lines.append("## %s" % section)
        for index, item in enumerate(items, start=1):
            lines.append(
                "%s. 제목: %s\n"
                "   출처: %s\n"
                "   날짜: %s\n"
                "   검색요약: %s\n"
                "   본문추출: %s\n"
                "   링크: %s"
                % (
                    index,
                    item.get("title") or "",
                    item.get("source") or "",
                    item.get("published_at") or "",
                    item.get("description") or "",
                    item.get("article_text") or "본문 추출 없음",
                    item.get("original_link") or item.get("link") or "",
                )
            )
        lines.append("")
    return "\n".join(lines).strip()


def _format_disclosures_for_prompt(disclosures):
    if not disclosures:
        return "관심 종목 공시는 수집되지 않았습니다."

    lines = []
    for index, item in enumerate(disclosures, start=1):
        lines.append(
            "%s. 회사: %s\n"
            "   보고서: %s\n"
            "   접수일: %s\n"
            "   링크: %s"
            % (
                index,
                item.get("corp_name") or "",
                item.get("report_name") or "",
                item.get("received_at") or "",
                item.get("link") or "",
            )
        )
    return "\n".join(lines)


def build_codex_prompt(news_items, disclosures, generated_at):
    return (
        "아래는 Market Brief Bot이 Naver Search API와 OpenDART API로 수집한 "
        "뉴스/공시 데이터입니다.\n\n"
        "요청:\n"
        "- 텔레그램 브리핑 상단에 넣을 한국어 요약문만 작성해 주세요.\n"
        "- 4~6개 bullet로 간결하게 작성해 주세요.\n"
        "- 각 bullet은 한 문장으로 작성하고 너무 길게 쓰지 마세요.\n"
        "- 본문추출이 있는 기사는 본문 내용을 우선 근거로 요약해 주세요.\n"
        "- 본문추출이 없는 기사는 제목/검색요약만 근거로 하므로 그 한계를 감안해 주세요.\n"
        "- 반복해서 등장하는 테마, 섹터, 관심 종목 흐름을 정리해 주세요.\n"
        "- 공시가 없으면 공시가 확인되지 않았다고만 써 주세요.\n"
        "- 매수/매도 추천, 목표가, 손절가, 확정적 수익 표현은 절대 쓰지 마세요.\n"
        "- 투자 판단이 아니라 정보 정리 관점으로만 작성해 주세요.\n"
        "- 원문 기사 문장을 길게 그대로 복사하지 마세요.\n"
        "- 출력에는 제목 없이 bullet 목록만 포함해 주세요.\n\n"
        "생성 시각: %s\n\n"
        "[뉴스 데이터]\n%s\n\n"
        "[DART 공시 데이터]\n%s\n"
        % (
            generated_at.strftime("%Y-%m-%d %H:%M"),
            _format_news_for_prompt(news_items) or "수집된 뉴스가 없습니다.",
            _format_disclosures_for_prompt(disclosures),
        )
    )


def _codex_command(output_path, cwd, model=None):
    codex_path = shutil.which("codex")
    if not codex_path:
        raise RuntimeError("codex CLI를 찾을 수 없습니다.")

    args = [
        "exec",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "-C",
        str(cwd),
        "-o",
        str(output_path),
    ]
    if model:
        args.extend(["-m", model])
    args.append("-")

    if sys.platform.startswith("win") and codex_path.lower().endswith(".ps1"):
        return [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            codex_path,
        ] + args

    return [codex_path] + args


def summarize_with_codex(news_items, disclosures, output_dir, generated_at, model=None, timeout=300, cwd=None):
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = generated_at.strftime("%Y%m%d_%H%M%S")
    prompt_path = output_dir / ("codex_prompt_%s.md" % stamp)
    output_path = output_dir / ("codex_summary_%s.md" % stamp)
    prompt = build_codex_prompt(news_items, disclosures, generated_at)
    prompt_path.write_text(prompt, encoding="utf-8")

    command = _codex_command(output_path, cwd or output_dir.parent, model=model)
    completed = subprocess.run(
        command,
        input=prompt,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        cwd=str(cwd or output_dir.parent),
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError("codex exec 실패(exit %s): %s" % (completed.returncode, detail[-1000:]))

    if not output_path.exists():
        raise RuntimeError("codex 요약 결과 파일이 생성되지 않았습니다: %s" % output_path)

    summary = output_path.read_text(encoding="utf-8").strip()
    if not summary:
        raise RuntimeError("codex 요약 결과가 비어 있습니다.")

    return SummaryResult(summary=summary, prompt_path=prompt_path, output_path=output_path)
