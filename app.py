import streamlit as st
import pandas as pd
import random
from itertools import combinations
import numpy as np
from collections import Counter

# --- Helper Functions (Backend Logic) ---

def generate_participant_list(company_participants):
    """会社ごとの参加者数から参加者リストを生成する"""
    participants = []
    participant_id = 1
    company_letter = 'A'
    for num in company_participants:
        for _ in range(num):
            participants.append({'id': participant_id, 'company': company_letter})
            participant_id += 1
        company_letter = chr(ord(company_letter) + 1)
    return participants

def analyze_company_duplicates(group):
    """グループ内の企業重複を分析し、文字列として返す"""
    if not group:
        return "なし"
    
    company_counts = Counter(p['company'] for p in group)
    duplicates = {company: count for company, count in company_counts.items() if count > 1}
    
    if not duplicates:
        return "なし"
    
    # 文字列にフォーマット: "会社A: 2名, 会社B: 2名"
    return ", ".join([f"会社{company}: {count}名" for company, count in sorted(duplicates.items())])

def create_day_grouping(participants, num_groups, existing_pairs):
    """
    1日分のグループ分けを作成する。重複を許容しつつ、最適な配置を探す。
    """
    if not participants:
        return []
    
    total_participants = len(participants)
    group_size = total_participants // num_groups
    # 人数が割り切れない場合のあまり
    remainder = total_participants % num_groups

    # 各グループの目標人数を計算
    group_capacities = [group_size + 1 if i < remainder else group_size for i in range(num_groups)]

    # 複数回試行してベストなものを探す
    best_grouping = None
    min_overall_score = float('inf')

    for _ in range(100): # 試行回数
        current_grouping = [[] for _ in range(num_groups)]
        temp_participants = random.sample(participants, len(participants))
        
        assignment_successful = True
        for p in temp_participants:
            available_groups_indices = [i for i, g in enumerate(current_grouping) if len(g) < group_capacities[i]]
            
            if not available_groups_indices:
                assignment_successful = False
                break
            
            # 各グループへの割り当てスコアを計算
            group_scores = []
            for i in available_groups_indices:
                group = current_grouping[i]
                # 企業の重複には高いペナルティを課す
                company_penalty = 100 * sum(1 for m in group if m['company'] == p['company'])
                # 過去の同席回数もスコアに加える
                co_occurrence_score = sum(existing_pairs.get(tuple(sorted((p['id'], m['id']))), 0) for m in group)
                total_score = company_penalty + co_occurrence_score
                group_scores.append((total_score, i))
            
            # 最もスコアの低い（=最も良い）グループに割り当て
            best_group_index = min(group_scores, key=lambda x: x[0])[1]
            current_grouping[best_group_index].append(p)
        
        if assignment_successful:
             # この日のグループ分けの総合スコアを計算（企業重複と個人重複の合計）
            current_overall_score = 0
            for group in current_grouping:
                # 企業重複のスコア
                company_counts = Counter(p['company'] for p in group)
                current_overall_score += sum(count - 1 for count in company_counts.values() if count > 1) * 100
                # 個人重複のスコア
                for p1, p2 in combinations(group, 2):
                    pair = tuple(sorted((p1['id'], p2['id'])))
                    current_overall_score += existing_pairs.get(pair, 0)
            
            if current_overall_score < min_overall_score:
                min_overall_score = current_overall_score
                best_grouping = current_grouping

    return best_grouping

def generate_all_days(participants, num_days, num_groups):
    """複数日分のグループ分けプラン全体を生成する"""
    all_day_groups = []
    co_occurrence = {}

    for day in range(num_days):
        day_grouping = create_day_grouping(participants, num_groups, co_occurrence)
        
        if not day_grouping:
            st.error(f"**{day+1}日目**のグループ分けに失敗しました。条件が複雑すぎる可能性があります。")
            return None, None

        all_day_groups.append(day_grouping)
        
        for group in day_grouping:
            for p1, p2 in combinations(group, 2):
                pair = tuple(sorted((p1['id'], p2['id'])))
                co_occurrence[pair] = co_occurrence.get(pair, 0) + 1
    
    return all_day_groups, co_occurrence

def style_matrix(df):
    """マトリクスのスタイルを設定する関数"""
    def highlight_cells(val):
        if val >= 2:
            return 'background-color: #FFE6E6'  # 淡い赤色
        return ''
    
    return df.style.applymap(highlight_cells)

# --- Streamlit App (Frontend) ---
st.set_page_config(layout="wide")
st.title('研修グループ分けアプリ 研修楽々くん')

with st.sidebar:
    st.header('研修の条件を入力してください')
    
    num_companies = st.number_input('会社の数', min_value=1, value=12, step=1)
    
    company_participants = []
    st.write("会社ごとの参加人数:")
    cols = st.columns(2)
    for i in range(num_companies):
        company_letter = chr(ord('A') + i)
        default_value = {0:2, 1:2, 2:3, 3:2, 4:1, 5:3, 6:2, 7:2, 8:2, 9:2, 10:2, 11:2}.get(i, 1)
        num = cols[i % 2].number_input(f'会社 {company_letter}', min_value=1, value=default_value, step=1, key=f"company_{i}")
        company_participants.append(num)

    total_participants = sum(company_participants)
    
    num_days = st.number_input('研修の日数', min_value=1, value=3, step=1)
    num_groups = st.number_input('1日あたりのグループ数', min_value=1, value=5, step=1)

    st.info(f"**合計参加人数:** {total_participants}名")
    
    # 警告メッセージの表示
    max_per_company = max(company_participants) if company_participants else 0
    if max_per_company > num_groups:
        st.warning(f'注意: 最も人数の多い会社（{max_per_company}名）がグループ数（{num_groups}）を上回っているため、グループ内で企業重複が必ず発生します。')
    if total_participants % num_groups != 0:
        st.warning('合計参加人数がグループ数で割り切れないため、グループごとの人数が均等になりません。')

if st.sidebar.button('グループ分けを作成する'):
    participants = generate_participant_list(company_participants)
    
    # ■追加1: 参加者リストの表示
    st.header('👥 参加者リスト')
    participant_data = []
    for p in participants:
        participant_data.append([p['id'], p['company']])
    
    df_participants = pd.DataFrame(participant_data, columns=['受講者ナンバー', '会社'])
    st.table(df_participants.set_index('受講者ナンバー'))
    
    all_day_groups, co_occurrence = generate_all_days(participants, num_days, num_groups)

    if all_day_groups:
        st.header('✅ グループ分けの結果')
        
        for i, day_grouping in enumerate(all_day_groups):
            st.subheader(f'📅 {i+1}日目')
            
            display_data = []
            max_group_size = 0
            for g_idx, group in enumerate(day_grouping):
                if len(group) > max_group_size:
                    max_group_size = len(group)
                
                group_members = [f"{p['id']}({p['company']})" for p in sorted(group, key=lambda x: x['id'])]
                duplicate_info = analyze_company_duplicates(group)
                display_data.append([f"グループ{g_idx+1}"] + group_members + [duplicate_info])
            
            # パディングしてDFの形状を統一
            for row in display_data:
                while len(row) < max_group_size + 2:
                    row.insert(-1, "") # 空白をメンバーリストの末尾に追加

            columns = ['グループ名'] + [f'メンバー{j+1}' for j in range(max_group_size)] + ['企業重複']
            df_day = pd.DataFrame(display_data, columns=columns)
            st.table(df_day.set_index('グループ名'))

        st.header('🤝 参加者の重複回数（マトリクス）')
        st.info('縦軸と横軸の参加者番号が交差する数字が、研修全体で同じグループになった回数です。2以上の場合は色付きで表示されます。')
        
        size = len(participants)
        matrix = np.zeros((size, size), dtype=int)
        for pair, count in co_occurrence.items():
            p1_idx, p2_idx = pair[0] - 1, pair[1] - 1
            matrix[p1_idx, p2_idx] = count
            matrix[p2_idx, p1_idx] = count
        
        df_matrix = pd.DataFrame(matrix, index=range(1, size + 1), columns=range(1, size + 1))
        
        # ■修正2: マトリクスに色付け機能を追加
        styled_matrix = style_matrix(df_matrix)
        st.dataframe(styled_matrix)
else:
    st.info('サイドバーで条件を入力し、「グループ分けを作成する」ボタンを押してください。')
