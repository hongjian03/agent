import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
import re


def Label_processing(merge_df):
    """标签处理"""


def label_merge(merge_df):
    """标签转换"""
    result_df = merge_df.copy()
    
    
    # 从院校层次提取标签
    def extract_school_level_tags(row):
        if pd.isna(row['院校层次']):
            return pd.Series({'名校申请经验丰富': '', '顶级名校成功案例': ''})
        
        tags = str(row['院校层次']).split('、')
        result = {
            '名校申请经验丰富': [],
            '顶级名校成功案例': []
        }
        
        # 检查每个标签是否包含关键词
        for tag in tags:
            if '名校申请经验丰富' in tag:
                result['名校申请经验丰富'].append(tag)  # 保留完整标签（包含国家名）
            if '顶级名校成功案例' in tag:
                result['顶级名校成功案例'].append(tag)  # 保留完整标签（包含国家名）
        
        return pd.Series({
            k: '、'.join(v) if v else '' for k, v in result.items()
        })
    
    # 从特殊项目标签提取标签
    def extract_special_project_tags(row):
        if pd.isna(row['特殊项目标签']):
            return pd.Series({
                '博士成功案例': '', 
                '博士申请经验': '', 
                '低龄留学成功案例': '', 
                '低龄留学申请经验': ''
            })
        
        tags = str(row['特殊项目标签']).split('、')
        result = {
            '博士成功案例': [],
            '博士申请经验': [],
            '低龄留学成功案例': [],
            '低龄留学申请经验': []
        }
        
        # 检查每个标签是否包含关键词
        for tag in tags:
            if '博士成功案例' in tag:
                result['博士成功案例'].append(tag)
            if '博士申请经验' in tag:
                result['博士申请经验'].append(tag)
            if '低龄留学成功案例' in tag:
                result['低龄留学成功案例'].append(tag)
            if '低龄留学申请经验' in tag:
                result['低龄留学申请经验'].append(tag)
        
        # 将列表转换为逗号分隔的字符串
        return pd.Series({
            k: '、'.join(v) if v else '' for k, v in result.items()
        })
    
    # 提取标签
    school_level_tags = result_df.apply(extract_school_level_tags, axis=1)
    special_project_tags = result_df.apply(extract_special_project_tags, axis=1)
    
    # 合并所有标签
    result_df = pd.concat([
        result_df['序号'],
        result_df['文案顾问业务单位'],
        result_df['国家标签'],
        result_df['专业标签'],
        school_level_tags,
        special_project_tags,
        result_df['行业经验'],
        result_df['文案背景'],
        result_df['业务单位所在地']
    ], axis=1)
    
    # 确保列的顺序正确
    desired_columns = [
        "序号", "文案顾问业务单位", "国家标签", "专业标签", 
        "名校申请经验丰富", "顶级名校成功案例",
        "博士成功案例", "博士申请经验", 
        "低龄留学成功案例", "低龄留学申请经验",
        "行业经验", "文案背景", "业务单位所在地",
    ]
    
    # 确保所有列都存在，如果不存在则添加空列
    for col in desired_columns:
        if col not in result_df.columns:
            result_df[col] = ''
    
    # 按照期望的顺序重排列
    result_df = result_df[desired_columns]
    
    return result_df

def Consultant_matching(consultant_tags_file, merge_df):
    """顾问匹配"""
        
    # 定义标签权重
    global tag_weights
    tag_weights = {
        '绝对高频国家': 20,
        '相对高频国家': 15,
        '绝对高频专业': 15,
        '相对高频专业': 10,
        '名校申请经验丰富': 10,
        '顶级名校成功案例': 10,
        '博士成功案例': 10,
        '博士申请经验': 10,
        '低龄留学成功案例': 10,
        '低龄留学申请经验': 10,
        '行业经验': 15,
        '文案背景': 10,
        '业务单位所在地': 15
    }
        
        
    # 定义工作量权重
    global workload_weights
    workload_weights = {
        '学年负荷': 50,
        '近两周负荷': 50
    }
        
    # 定义个人意愿权重
    global personal_weights
    personal_weights = {
        '个人意愿': 100,
    }
        
    # 定义评分维度权重
    global dimension_weights
    dimension_weights = {
        '标签匹配': 0.5,
        '工作量': 0.3,
        '个人意愿': 0.2
    }

    def calculate_tag_matching_score(case, consultant):
        """计算标签匹配得分"""
        tag_score_dict = {}  # 用于存储每个标签的得分
        
        # 1. 国家标签匹配
        if '国家标签' in case and pd.notna(case['国家标签']):
            # 处理案例国家
            raw_case_countries = case['国家标签']
            
            split_case_countries = re.split(r'[、,，]+', raw_case_countries)
            
            case_countries = {country.strip() for country in split_case_countries}
            
            # 处理顾问国家
            raw_absolute = consultant['绝对高频国家'] if pd.notna(consultant['绝对高频国家']) else ''
            raw_relative = consultant['相对高频国家'] if pd.notna(consultant['相对高频国家']) else ''
            absolute_high_freq = {country.strip() for country in re.split(r'[、,，]+', raw_absolute)} if raw_absolute else set()
            relative_high_freq = {country.strip() for country in re.split(r'[、,，]+', raw_relative)} if raw_relative else set()
            # 检查是否完全包含目标国家
            if case_countries.issubset(absolute_high_freq):
                tag_score_dict['绝对高频国家'] = tag_weights['绝对高频国家']
            elif case_countries.issubset(absolute_high_freq.union(relative_high_freq)):
                tag_score_dict['相对高频国家'] = tag_weights['相对高频国家']
                

        # 2. 专业标签匹配
        if '专业标签' in case and pd.notna(case['专业标签']):
            case_majors = set(re.split(r'[、,，\s]+', case['专业标签']))
            absolute_high_freq_majors = set(re.split(r'[、,，\s]+', consultant['绝对高频专业'])) if pd.notna(consultant['绝对高频专业']) else set()
            relative_high_freq_majors = set(re.split(r'[、,，\s]+', consultant['相对高频专业'])) if pd.notna(consultant['相对高频专业']) else set()
            
            if case_majors.issubset(absolute_high_freq_majors):
                tag_score_dict['绝对高频专业'] = tag_weights['绝对高频专业']
            elif case_majors.issubset(absolute_high_freq_majors.union(relative_high_freq_majors)):
                tag_score_dict['相对高频专业'] = tag_weights['相对高频专业']
        
        # 3. 其他标签匹配（需要完全包含）
        special_tags = [
            '名校申请经验丰富', '顶级名校成功案例', '博士成功案例', '博士申请经验',
            '低龄留学成功案例', '低龄留学申请经验'
        ]
        
        for tag in special_tags:
            if pd.notna(case[tag]) and pd.notna(consultant[tag]) and case[tag] != '':
                # 将case和consultant的标签都分割成集合
                case_tags = set(re.split(r'[、,，\s]+', case[tag]))
                consultant_tags = set(re.split(r'[、,，\s]+', consultant[tag]))
                
                # 检查consultant的标签是否包含case所需的所有标签
                if case_tags.issubset(consultant_tags):
                    tag_score_dict[tag] = tag_weights[tag]


        # 4. 行业经验标签匹配（反向包含关系：consultant的标签要包含在case中）
        if pd.notna(case['行业经验']) and pd.notna(consultant['行业经验']) and case['行业经验'] != '':
            case_industry = set(re.split(r'[、,，\s]+', case['行业经验']))
            consultant_industry = set(re.split(r'[、,，\s]+', consultant['行业经验']))
            
            # 检查consultant的行业经验是否被case的行业经验包含
            if consultant_industry.issubset(case_industry):
                tag_score_dict['行业经验'] = tag_weights['行业经验']
        
        # 5. 直接匹配标签（不需要分割）
        direct_match_tags = [
            '文案背景',
            '业务单位所在地'
        ]
        
        for tag in direct_match_tags:
            if pd.notna(case[tag]) and pd.notna(consultant[tag]):
                if case[tag] == consultant[tag] and case[tag] != '':
                    tag_score_dict[tag] = tag_weights[tag]
        
        return  tag_score_dict



    def calculate_workload_score(case, consultant):
        """计算工作量得分"""
        total_score = 0
        
        # 检查学年负荷
        if pd.notna(consultant['学年负荷']):
            value = str(consultant['学年负荷']).lower()
            if value in ['是', 'true', 'yes','有余量']:
                total_score += workload_weights['学年负荷']  # 50分
        
        # 检查近两周负荷
        if pd.notna(consultant['近两周负荷']):
            value = str(consultant['近两周负荷']).lower()
            if value in ['是', 'true', 'yes','有余量']:
                total_score += workload_weights['近两周负荷']  # 50分
        
        return total_score

    def calculate_personal_score(case, consultant):
        """计算个人意愿得分"""
        total_score = 0
        
        # 检查个人意愿
        if pd.notna(consultant['个人意愿']):
            value = str(consultant['个人意愿']).lower()
            if value in ['是', 'true', 'yes','接案中']:
                total_score += personal_weights['个人意愿']  # 100分
        
        
        return total_score

    def calculate_final_score(tag_score_dict, consultant, workload_score, personal_score, case):
        """计算最终得分（包含所有维度）"""
        def count_matched_tags(tag_score_dict, case):
            """计算匹配上的标签数量"""
            country_count_need = 0
            special_count_need = 0
            other_count_need = 0
            
            # 国家标签匹配计算
            if any(score > 0 for tag, score in tag_score_dict.items() 
                   if tag in ['绝对高频国家', '相对高频国家']):
                # 获取案例中的国家数量
                case_countries = set(re.split(r'[、,，\s]+', case['国家标签'])) if pd.notna(case['国家标签']) else set()
                country_count_need += len(case_countries)
            
            # 特殊标签如果得分，获取案例中对应标签的数量
            special_tags = ['名校申请经验丰富', '顶级名校成功案例', '博士成功案例', '博士申请经验', 
                            '低龄留学成功案例', '低龄留学申请经验']
    
            for tag in special_tags:
                if tag_score_dict.get(tag, 0) > 0 and pd.notna(case[tag]) and case[tag] != '':
                    tag_items = set(re.split(r'[、,，\s]+', case[tag]))
                    special_count_need += len(tag_items)

            # 其他标签只要得分就计数
            other_tags = ['绝对高频专业', '相对高频专业', '行业经验', '文案背景', 
                          '业务单位所在地']
            for tag in other_tags:
                if tag_score_dict.get(tag, 0) > 0:
                    other_count_need += 1
            
            return country_count_need, special_count_need, other_count_need

        def count_total_consultant_tags(consultant):
            """计算顾问的总标签数"""
            country_count_total = 0
            special_count_total = 0
            other_count_total = 0
            
            # 计算国家标签数
            absolute_high_freq = set(re.split(r'[、,，\s]+', consultant['绝对高频国家'])) if pd.notna(consultant['绝对高频国家']) else set()
            relative_high_freq = set(re.split(r'[、,，\s]+', consultant['相对高频国家'])) if pd.notna(consultant['相对高频国家']) else set()
            country_count_total += len(absolute_high_freq) + len(relative_high_freq)
            
            # 计算特殊标签数
            special_tags = ['顶级名校成功案例', '博士成功案例', '博士申请经验', 
                            '低龄留学成功案例', '低龄留学申请经验']
    
            for tag in special_tags:
                if pd.notna(consultant[tag]) and consultant[tag] != '':
                    tag_items = set(re.split(r'[、,，\s]+', consultant[tag]))
                    special_count_total += len(tag_items)
            
            # 计算其他标签数
            other_tags = ['绝对高频专业', '相对高频专业','名校申请经验丰富', '行业经验', '文案背景', 
                          '业务单位所在地']
            for tag in other_tags:
                if pd.notna(consultant[tag]) and consultant[tag] != '':
                    other_count_total += 1
                
            return country_count_total, special_count_total, other_count_total
        
        # 计算标签匹配率
        country_count_need, special_count_need, other_count_need = count_matched_tags(tag_score_dict, case)
        country_count_total, special_count_total, other_count_total = count_total_consultant_tags(consultant)
        
        # 计算匹配率
        country_match_ratio = country_count_need / country_count_total if country_count_total > 0 else 0
        special_match_ratio = special_count_need / special_count_total if special_count_total > 0 else 0
        
        # 分别计算国家标签、特殊标签和其他标签的得分
        country_tags_score = sum(score for tag, score in tag_score_dict.items() if tag in ['绝对高频国家', '相对高频国家'])
        special_tags_score = sum(score for tag, score in tag_score_dict.items() if tag in [
            '顶级名校成功案例', '博士成功案例', '博士申请经验', 
            '低龄留学成功案例', '低龄留学申请经验'
        ])
        other_tags_score = sum(score for tag, score in tag_score_dict.items() if tag not in [
            '绝对高频国家', '相对高频国家', '顶级名校成功案例', 
            '博士成功案例', '博士申请经验', '低龄留学成功案例', '低龄留学申请经验'
        ])
        
        # 计算需求标签数
        case_country_count = len(set(re.split(r'[、,，\s]+', case['国家标签']))) if pd.notna(case['国家标签']) else 0
        
        case_special_count = 0
        special_tags = ['名校申请经验丰富', '顶级名校成功案例', '博士成功案例', '博士申请经验', 
                        '低龄留学成功案例', '低龄留学申请经验']
        for tag in special_tags:
            if pd.notna(case[tag]) and case[tag] != '':
                case_special_count += len(set(re.split(r'[、,，\s]+', case[tag])))
        
        # 计算需求覆盖率
        country_coverage_ratio = country_count_need / case_country_count if case_country_count > 0 else 0
        special_coverage_ratio = special_count_need / case_special_count if case_special_count > 0 else 0
        
        # 应用匹配率和覆盖率到对应标签得分上
        adjusted_country_score = country_tags_score * country_match_ratio * country_coverage_ratio
        adjusted_special_score = special_tags_score * special_match_ratio * special_coverage_ratio
        
        # 计算调整后的总标签得分
        adjusted_tag_score = adjusted_country_score + adjusted_special_score + other_tags_score
        
        
        # 计算各维度最终得分
        final_tag_score = (adjusted_tag_score / 100) * dimension_weights['标签匹配'] * 100
        final_workload_score = (workload_score / 100) * dimension_weights['工作量'] * 100
        final_personal_score = (personal_score / 100) * dimension_weights['个人意愿'] * 100
        
        
        # 更新返回结果，添加覆盖率信息
        result = {
            'score': final_tag_score + final_workload_score + final_personal_score,
            'country_count_need': country_count_need,
            'special_count_need': special_count_need,
            'other_count_need': other_count_need,
            'country_count_total': country_count_total,
            'special_count_total': special_count_total,
            'other_count_total': other_count_total,
            'country_match_ratio': country_match_ratio,
            'special_match_ratio': special_match_ratio,
            'country_coverage_ratio': country_coverage_ratio,
            'special_coverage_ratio': special_coverage_ratio,
            'country_tags_score': country_tags_score,
            'special_tags_score': special_tags_score,
            'other_tags_score': other_tags_score
        }
        
        return result

    def find_best_matches(consultant_tags_file, merge_df, area):
        """找到每条案例得分最高的顾问们"""
        # 存储所有案例的匹配结果
        all_matches = {}
        all_tag_score_dicts = {}  # 存储每个案例的所有顾问得分字典
        all_workload_score_dicts = {}  # 存储每个案例的所有顾问工作量得分字典
        all_completion_rate_score_dicts = {}  # 存储每个案例的所有顾问完成率得分字典
        all_local_consultants = {}
        # 对每条案例进行匹配
        for idx, case in merge_df.iterrows():
            scores = []
            case_tag_score_dicts = {}  # 存储当前案例的所有顾问得分字典
            case_workload_score_dicts = {}  # 存储当前案例的所有顾问工作量得分字典
            case_completion_rate_score_dicts = {}  # 存储当前案例的所有顾问完成率得分字典
            
            # 选择顾问范围（本地或全部）
            local_consultants = consultant_tags_file[consultant_tags_file['文案顾问业务单位'] == case['文案顾问业务单位']]
            all_consultants = consultant_tags_file
            consultants = local_consultants if area else all_consultants
            all_local_consultants[case['序号']] = local_consultants
            # 计算每个顾问对当前案例的得分
            for cidx, consultant in consultants.iterrows():
                try:
                    # 获取标签匹配得分和得分字典
                    tag_score_dict = calculate_tag_matching_score(case, consultant)
                    workload_score = calculate_workload_score(case, consultant)
                    personal_score = calculate_personal_score(case, consultant)
                    # 计算最终得分
                    final_result = calculate_final_score(
                        tag_score_dict,
                        consultant,
                        workload_score,
                        personal_score,
                        case
                    )
                    
                    # 保存当前顾问的得分字典
                    case_tag_score_dicts[consultant['文案顾问']] = tag_score_dict
                    case_workload_score_dicts[consultant['文案顾问']] = workload_score
                    case_completion_rate_score_dicts[consultant['文案顾问']] = consultant['完成率']
                    
                    # 获取顾问的标签数据
                    consultant_info = {
                        'name': consultant['文案顾问'],
                        'businessunits': consultant['文案顾问业务单位'],
                        'area':area,
                        'score': final_result['score'],
                        'tag_score_dict': tag_score_dict,
                        'workload_score': workload_score,
                        'personal_score': personal_score,
                        'country_count_need': final_result['country_count_need'],
                        'special_count_need': final_result['special_count_need'],
                        'other_count_need': final_result['other_count_need'],
                        'country_count_total': final_result['country_count_total'],
                        'special_count_total': final_result['special_count_total'],
                        'other_count_total': final_result['other_count_total'],
                        'country_match_ratio': final_result['country_match_ratio'],
                        'special_match_ratio': final_result['special_match_ratio'],
                        'country_coverage_ratio': final_result['country_coverage_ratio'],
                        'special_coverage_ratio': final_result['special_coverage_ratio'],
                        'country_tags_score': final_result['country_tags_score'],
                        'special_tags_score': final_result['special_tags_score'],
                        'other_tags_score': final_result['other_tags_score']
                    }
                    
                    # 安全地添加标签字段
                    standard_fields = [
                        '绝对高频国家', '相对高频国家', '绝对高频专业', '相对高频专业', 
                        '行业经验', '业务单位所在地', '学年负荷', '近两周负荷', '个人意愿',
                        '名校申请经验丰富', '顶级名校成功案例', '博士成功案例', 
                        '博士申请经验', '低龄留学成功案例', '低龄留学申请经验'
                    ]
                    
                    for field in standard_fields:
                        if field in consultant.index and pd.notna(consultant[field]):
                            consultant_info[field] = consultant[field]
                        else:
                            consultant_info[field] = ''
                    
                    scores.append(consultant_info)
                except Exception as e:
                    st.error(f"计算得分出错: {str(e)}")
            
            # 按得分降序排序
            scores.sort(key=lambda x: -x['score'])
            
            # 获取最高分
            highest_score = scores[0]['score'] if scores else 0
            # 获取第九高分（如果存在）
            ninth_score = scores[8]['score'] if len(scores) > 8 else None
            
            # 选择得分最高的顾问们
            selected_consultants = []
            for s in scores:
                if (ninth_score is not None and s['score'] >= ninth_score) or (ninth_score is None and s['score'] == highest_score):
                    consultant_data = {
                        'display': f"{s['name']}（{s['score']:.1f}分）",
                        'name': s['name'],
                        'businessunits': s['businessunits'],
                        'area':s['area'],
                        'score': s['score'],
                        'tag_score_dict': s['tag_score_dict'],
                        'workload_score': s['workload_score'],
                        'personal_score': s['personal_score'],
                        'country_count_need': s['country_count_need'],
                        'special_count_need': s['special_count_need'],
                        'other_count_need': s['other_count_need'],
                        'country_count_total': s['country_count_total'],
                        'special_count_total': s['special_count_total'],
                        'other_count_total': s['other_count_total'],
                        'country_match_ratio': s['country_match_ratio'],
                        'special_match_ratio': s['special_match_ratio'],
                        'country_coverage_ratio': s['country_coverage_ratio'],
                        'special_coverage_ratio': s['special_coverage_ratio'],
                        'country_tags_score': s['country_tags_score'],
                        'special_tags_score': s['special_tags_score'],
                        'other_tags_score': s['other_tags_score']
                    }
                    
                    # 复制其他标签字段
                    for field in standard_fields:
                        if field in s:
                            consultant_data[field] = s[field]
                    
                    selected_consultants.append(consultant_data)
            
            # 存储当前案例的匹配结果和所有顾问的得分字典
            case_key = f"案例{idx + 1}"
            all_matches[case_key] = selected_consultants
            all_tag_score_dicts[case_key] = case_tag_score_dicts
            all_workload_score_dicts[case_key] = case_workload_score_dicts
            all_completion_rate_score_dicts[case_key] = case_completion_rate_score_dicts
        

        return all_matches, all_tag_score_dicts, all_workload_score_dicts, all_completion_rate_score_dicts
    
    # 1. 先计算本地顾问的得分
    area = True
    local_scores, all_tag_score_dicts, all_workload_score_dicts, all_completion_rate_score_dicts = find_best_matches(consultant_tags_file, merge_df, area)

    # 2. 检查7个判断条件
    def all_conditions_met(all_tag_score_dicts, all_workload_score_dicts, all_completion_rate_score_dicts, case,idx):
        # 获取所有顾问列表
        consultants = set(all_tag_score_dicts["案例1"].keys())
        
        idx_case = f"案例{idx+1}"
        # 对每个顾问单独判断所有条件
        for consultant in consultants:
            # 初始化该顾问的标志
            consultant_conditions = {
                '国家标签': False,
                '专业标签': False,
                '顶级名校成功案例': False,
                '博士申请经验': False,
                '低龄留学申请经验': False,
                '行业经验': False,
                '工作量': False,
                '完成率': False
            }
            
            # 1. 国家和专业标签判断
            has_country = True if case['国家标签'] != '' else False
            has_major = True if case['专业标签'] != '' else False

            if has_country or has_major:
                tag_score_dicts = all_tag_score_dicts[idx_case]
                tag_score_dict = tag_score_dicts[consultant]
                for tag, score in tag_score_dict.items():
                    if tag in ['绝对高频国家', '相对高频国家']:
                        if score > 0:
                            consultant_conditions['国家标签'] = True
                    if tag in ['绝对高频专业', '相对高频专业']:
                        if score > 0:
                            consultant_conditions['专业标签'] = True
            else:
                consultant_conditions['国家标签'] = True
                consultant_conditions['专业标签'] = True
    
            # 2. 顶级名校成功案例标签判断
            has_school = True if case['顶级名校成功案例'] != '' else False
            if has_school:
                tag_score_dicts = all_tag_score_dicts[idx_case]
                tag_score_dict = tag_score_dicts[consultant]
                if '顶级名校成功案例' in tag_score_dict and tag_score_dict['顶级名校成功案例'] > 0:
                    consultant_conditions['顶级名校成功案例'] = True
            else:
                consultant_conditions['顶级名校成功案例'] = True
            # 3. 博士申请经验标签判断
            has_doctor = True if case['博士申请经验'] != '' else False
            if has_doctor:
                tag_score_dicts = all_tag_score_dicts[idx_case]
                tag_score_dict = tag_score_dicts[consultant]
                if '博士申请经验' in tag_score_dict and tag_score_dict['博士申请经验'] > 0:
                    consultant_conditions['博士申请经验'] = True
            else:
                consultant_conditions['博士申请经验'] = True
            # 4. 低龄留学申请经验标签判断
            has_lowage = True if case['低龄留学申请经验'] != '' else False
            if has_lowage:
                tag_score_dicts = all_tag_score_dicts[idx_case]
                tag_score_dict = tag_score_dicts[consultant]
                if '低龄留学申请经验' in tag_score_dict and tag_score_dict['低龄留学申请经验'] > 0:
                    consultant_conditions['低龄留学申请经验'] = True
            else:
                consultant_conditions['低龄留学申请经验'] = True
            # 5. 行业经验标签判断
            has_industry = True if '专家Lv.6+' in str(case['行业经验']) else False
            if has_industry:
                tag_score_dicts = all_tag_score_dicts[idx_case]
                tag_score_dict = tag_score_dicts[consultant]
                if '行业经验' in tag_score_dict and tag_score_dict['行业经验'] > 0:
                    consultant_conditions['行业经验'] = True
            else:
                consultant_conditions['行业经验'] = True
            # 6. 工作量标签判断
            workload_score_dicts = all_workload_score_dicts[idx_case]
            workload_score_dict = workload_score_dicts[consultant]
            if workload_score_dict > 0:
                consultant_conditions['工作量'] = True
            # 7. 完成率判断
            completion_rate_dicts = all_completion_rate_score_dicts[idx_case]
            completion_rate_dict = completion_rate_dicts[consultant]
            if pd.notna(completion_rate_dict):
                value = str(completion_rate_dict).lower()
                if value in ['true', 'yes', '是', 'true', '1']:
                    consultant_conditions['完成率'] = True
            # 如果这个顾问满足所有条件，直接返回True
            if all(consultant_conditions.values()):
                return True
                
            else:
                # 打印未满足的条件
                st.write(f"顾问 {consultant} 的条件状态：")
                for condition, is_met in consultant_conditions.items():
                    if not is_met:
                        st.write(f"  - 未满足: {condition}")

        # 如果没有任何顾问满足所有条件，返回False
        return False
    for idx,case in merge_df.iterrows():
        if all_conditions_met(all_tag_score_dicts, all_workload_score_dicts, all_completion_rate_score_dicts, case,idx):
            # 如果所有条件都满足，使用本地顾问的匹配结果
            return local_scores ,area
    else:
        # 如果有任何条件不满足，使用所有顾问重新计算匹配

        area = False
        all_scores,all_tag_score_dicts,all_workload_score_dicts,all_completion_rate_score_dicts = find_best_matches(consultant_tags_file, merge_df, area)
        return all_scores ,area

def match_main():
    st.title("顾问匹配系统")
    
    # 初始化 session_state
    if 'processed_df' not in st.session_state:
        st.session_state.processed_df = None
    if 'merged_df' not in st.session_state:
        st.session_state.merged_df = None
    
    # 文件上传区域
    with st.container():
        st.subheader("数据上传")
        uploaded_sample_data = st.file_uploader("请上传案例数据", type=['xlsx'], key='sample')
        uploaded_merge_data = st.file_uploader("请上传需要合并的主体数据表", type=['xlsx'], key='merge')
        uploaded_consultant_tags = st.file_uploader("请上传文案顾问标签汇总", type=['xlsx'], key='consultant')
        
        # 读取所有上传的文件
        if uploaded_sample_data is not None:
            sample_df = pd.read_excel(uploaded_sample_data)
            st.success("案例数据上传成功")
            
        if uploaded_merge_data is not None:
            merge_df = pd.read_excel(uploaded_merge_data)
            st.success("主体数据表上传成功")
            
        if uploaded_consultant_tags is not None:
            consultant_tags_df = pd.read_excel(uploaded_consultant_tags)
            st.success("顾问标签汇总上传成功")
    
    # 处理按钮区域
    with st.container():
        st.subheader("数据处理")
        col1, col2, col3 = st.columns(3)
        
        # 标签处理按钮
        
        # 标签合并按钮
        with col2:
            if st.button("开始标签合并"):
                if st.session_state.processed_df is not None and uploaded_merge_data is not None:
                    try:
                        st.session_state.merged_df = label_merge(st.session_state.processed_df, merge_df)
                        st.success("标签合并完成！")
                        # 显示合并后的数据预览
                        st.write("合并后数据预览：")
                        st.dataframe(st.session_state.merged_df.head())
                        
                        # 添加下载按钮
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            st.session_state.merged_df.to_excel(writer, index=False, sheet_name='标签合并结果')
                        st.download_button(
                            label="下载标签合并结果",
                            data=buffer.getvalue(),
                            file_name="标签合并结果.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"标签合并出错: {str(e)}")
                else:
                    st.warning("请先完成标签处理并上传主体数据表")
        
        # 顾问匹配按钮
        with col3:
            if st.button("开始顾问匹配"):
                if st.session_state.merged_df is not None and uploaded_consultant_tags is not None:
                    try:
                        # 调用顾问匹配函数
                        matching_results = Consultant_matching(
                            consultant_tags_df,
                            sample_df,
                            st.session_state.merged_df
                        )
                        st.success("顾问匹配完成！")
                        
                        # 将匹配结果添加到原始sample数据中
                        result_df = sample_df.copy()
                        result_df['匹配文案列表'] = ''
                        
                        # 将匹配结果填入对应行
                        for case, consultants in matching_results.items():
                            idx = int(case.replace('案例', '')) - 1
                            consultant_str = '；'.join(consultants)
                            result_df.loc[idx, '匹配文案列表'] = consultant_str
                        
                        # 显示结果预览
                        st.write("匹配结果预览：")
                        st.dataframe(result_df)
                        
                        # 添加下载按钮
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            result_df.to_excel(writer, index=False, sheet_name='顾问匹配结果')
                        st.download_button(
                            label="下载顾问匹配结果",
                            data=buffer.getvalue(),
                            file_name="顾问匹配结果.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"顾问匹配出错: {str(e)}")
                else:
                    st.warning("请先完成标签合并并上传顾问标签汇总")
    
    # 显示处理状态
    with st.container():
        st.subheader("处理状态")
        status_col1, status_col2, status_col3 = st.columns(3)
        with status_col1:
            st.write("标签处理状态:", "✅ 完成" if st.session_state.processed_df is not None else "⏳ 待处理")
        with status_col2:
            st.write("标签合并状态:", "✅ 完成" if st.session_state.merged_df is not None else "⏳ 待处理")
        with status_col3:
            st.write("顾问匹配状态:", "✅ 完成" if 'matching_results' in locals() else "⏳ 待处理")

if __name__ == "__main__":
    match_main()

#cd agent
#streamlit run match.py
