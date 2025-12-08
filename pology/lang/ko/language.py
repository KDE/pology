# -*- coding: UTF-8 -*

"""
Rules with dynamically generated regex. Some rules are adopted from ko-po-check.

@author: Shinjo Park <kde@peremen.name>
@original-author: Changwoo Ryu <cwryu@debian.org>
@license: GPLv3+
"""

import re

from pology import datadir, _, n_
from pology.diff import adapt_spans

PLURAL_JOSA_RE = r'(도|로|만|에|은|을|이|의)'
# 많이 등장하는 명사만 쓴다
PLURAL_NOUN_RE = r'(값|개발자|것|기능|기술|그림|글자|답변|디렉터리|메시지|' \
                 r'문서|문자|분|사람|사진|설정|언어|점|질문|파일|팀|패키지|' \
                 r'폴더|프로그램|플러그인|항목|활동)'
PLURAL_EXCEPT = r'(핸들|번들)' + PLURAL_JOSA_RE

PLURAL_R = re.compile(r'(' +
        r'[가-힣]+\(들\)' + r'|' +
        PLURAL_NOUN_RE + r'들' + r'|' +
        r'[가-힣]+들' + PLURAL_JOSA_RE + r'\s' + r')', re.UNICODE)
PLURAL_EXCLUDE = re.compile(PLURAL_EXCEPT, re.UNICODE)

def redundant_plural (msgstr, msg, cat):
    """
    불필요한 복수형 표현을 검사한다.

    임의의 복수형 표현을 찾아내기는 매우 힘들다. 다음 휴리스틱으로만 검사.
    (0) (들)이라고 쓰여진 경우
    (1) 일단 알려진 명사에 대한 복수형태를 찾고
    (2) 들+조사 형태로 끝나는 경우를 찾는다

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return check(PLURAL_R, PLURAL_EXCLUDE, msgstr, msg, cat, u"Unnecessary plural '%(match)s'.")

SYLLABLE_WITH_T_RIEUL = '[%s]' % ''.join([chr(c) for c in
                                          range(0xAC00 + 8, 0xD7A4, 28)])
SYLLABLE_WITH_T_SSANGSIOS = '[%s]' % \
                            ''.join([chr(c) for c in
                                     range(0xAC00 + 0x14, 0xD7A4, 28)])
GEOSIPNIDA_R = re.compile(r'\S+' + SYLLABLE_WITH_T_RIEUL + u' 것입니다')
# 과거형인 "-했을 것입니다"는 예외
GEOSIPNIDA_EXCLUDE = re.compile(r'\S+' + SYLLABLE_WITH_T_SSANGSIOS + u'을 것입니다')

def hal_geosipnida (msgstr, msg, cat):
    """
    ...할 것입니다

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return check(GEOSIPNIDA_R, GEOSIPNIDA_EXCLUDE, msgstr, msg, cat, "Try to revise '%(match)s'.")

def check(r, exclude, msgstr, msg, cat, errmsg):

    spans = []
    matches = list(r.finditer(msgstr))
    for m in matches:
        p1, p2 = m.span()
        if exclude and exclude.match(msgstr[p1:p2].strip()):
            continue
        spans.append((p1, p2, _(u"@info", errmsg, match=msgstr[p1:p2].strip())))

    return spans
