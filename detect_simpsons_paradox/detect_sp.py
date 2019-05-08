import pandas as pd
import numpy as np
import scipy.stats as stats
import itertools as itert

## constants

RESULTS_DF_HEADER_old = ['attr1','attr2','allCorr','subgroupCorr','groupbyAttr','subgroup']

RESULTS_DF_HEADER = ['feat1','feat2','trend_type','agg_trend','group_feat',
                    'subgroup','subgroup_trend']


from .trends import all_trend_types
# get_trend_vars = {'pearson_corr':lambda l_df: l_df.get_vars_per_roletype('trend'
#                                                             ,'continuous'),
#               'rate': lambda df: list(df.select_dtypes(include=['bool'])),
#               'rank': lambda df: [col for col in df.columns if col[-5:] == '_rate']
#                }
# get_trend_funcs = {'pearson_corr':get_correlations,
#                 'rank':get_rank_trends}




################################################################################
# helper Mixin class
################################################################################
class _detect_SP_trends():
    """
    a mixin class of detectors and trend computations
    """


    def get_SP_views(labeled_df,sp_type='SP',
                cols_pair = ['agg_trend','subgroup_trend'],
                colored=False):
        """
        return a list of tuples of the views of the dataset that have at least one
        occurence of SP. Assumes no views are listed in in opposite orders

        Parameters
        -----------
        results_df : DataFrame
            reustls generated by get_subgroup_trends_*
        sp_type : string or function handle
            SP type as defined by label_SP_rows()
        cols_pair : list of strings
            column anmes to be used in the SP detection
        colored : Boolean
            use 'colored' views or not if True, a view is defined by 2 features and
            a grouping variable, if False a view is defined by 2 features only

        Returns
        ---------
        sp_views_unique : list of tuples
            list of the view pairs

        """
        # add SP label if not already added
        col_name = '_'.join(cols_pair) + '_' + sp_type
        if not col_name in labeled_df.results_df.columns:
            labeled_df.label_SP_rows(sp_type,cols_pair)

        # filter
        sp_df = labeled_df.results_df[labeled_df.results_df[col_name] == True]

        # type cast back to list to return
        return get_views(sp_df,colored)

    def get_SP_rows(labeled_df,sp_type='SP',
                cols_pair = ['agg_trend','subgroup_trend'],
                colored=False, sp_args = None):
        """
        return a list of tuples of the rows of the dataset that have at least one
        occurence of SP.

        Parameters
        -----------
        results_df : DataFrame
            reustls generated by get_subgroup_trends_*
        sp_type : string or function handle
            SP type as defined by label_SP_rows()
        cols_pair : list of strings
            column anmes to be used in the SP detection
        colored : Boolean
            use 'colored' views or not if True, a view is defined by 2 features and
            a grouping variable, if False a view is defined by 2 features only

        Returns
        ---------
        sp_views_unique : list of tuples
            list of the view pairs

        """
        # add SP label if not already added
        col_name = '_'.join(cols_pair) + '_' + sp_type
        if not col_name in results_df.columns:
            labeled_df.label_SP_rows(sp_type,cols_pair, sp_args)

        # filter
        sp_df = labeled_df.results_df[results_df[col_name] == True]

        return sp_df



    def get_subgroup_trends_1lev(self,trend_types):
        """
        find subgroup and aggregate trends in the dataset, return a DataFrame that
        contains information necessary to filter for SP and relaxations
        computes for 1 level grouby (eg correlation and linear trends)

        Parameters
        -----------
        labeled_df : labeledDataFrame
            data to find SP in, must be tidy
        trend_types: list of strings or list trend objects
            info on what trends to compute and the variables to use, dict is of form
        {'name':<str>,'vars':['varname1','varname1'],'func':functionhandle}

        """
        data_df = self.df
        groupby_vars = self.get_vars_per_role('groupby')

        # if not specified, detect continous attributes and categorical attributes
        # from dataset
        if groupby_vars is None:
            groupby_data = self.df.select_dtypes(include=['object','int64'])
            groupby_vars = list(groupby_data)

        if type(trend_types[0]) is str:
            # instantiate objects
            trend_list = [all_trend_types[trend]() for trend in trend_types]
        else:
            # use provided
            trend_list = trend_types

        # prep the result df to add data to later
        self.result_df = pd.DataFrame(columns=RESULTS_DF_HEADER)

        # create empty lists
        all_trends = []
        subgroup_trends = []

        for cur_trend in trend_list:
            cur_trend.get_trend_vars(self)
            # Tabulate aggregate statistics
            agg_trends = cur_trend.get_trends(self.df,'agg_trend')

            all_trends.append(agg_trends)

            # iterate over groupby attributes
            for groupbyAttr in groupby_vars:
                #condition the data
                cur_grouping = self.df.groupby(groupbyAttr)

                # get subgoup trends
                curgroup_corr = cur_trend.get_trends(cur_grouping,'subgroup_trend')

                # append
                subgroup_trends.append(curgroup_corr)




        # condense and merge all trends with subgroup trends
        all_trends = pd.concat(all_trends)
        subgroup_trends = pd.concat(subgroup_trends)
        self.result_df = pd.merge(subgroup_trends,all_trends)
        # ,on=['feat1','feat2'], how='left

        return self.result_df

    def get_subgroup_trends_2lev(data_df,trend_types,groupby_vars=None):
        """
        find subgroup and aggregate trends in the dataset, return a DataFrame that
        contains information necessary to filter for SP and relaxations
        for 2 levels of groupby (eg rate trends)

        Parameters
        -----------
        data_df : DataFrame
            data to find SP in, must be tidy
        trend_types: list of strings or list of dicts
            info on what trends to compute and the variables to use, dict is of form
        {'name':<str>,'vars':['varname1','varname1'],'func':functionhandle}
        groupby_vars : list of strings or list of list of strings
            column names to use as grouping variables
        trend_vars : list of strings
            column names to use in regresison based trends
        rate_vars : list of strings
            column names to use in rate based trends
        trend_func : function handle
            to compute the trend
        """

        # if not specified, detect continous attributes and categorical attributes
        # from dataset
        if groupby_vars is None:
            groupby_data = data_df.select_dtypes(include=['object','int64'])
            groupby_vars = list(groupby_data)

        if type(trend_types[0]) is str:
            # create dict
            trend_dict_list = [{'name':trend,
                            'vars':get_trend_vars[trend](data_df),
                            'func':get_trend_funcs[trend]} for trend in trend_types]
        else:
            # use provided
            trend_dict_list = trend_types

        # prep the result df to add data to later
        result_df = pd.DataFrame(columns=RESULTS_DF_HEADER)

        # create empty lists
        all_trends = []
        subgroup_trends = []

        for td in trend_dict_list:
            trend_func = td['func']
            trend_vars = td['vars']
            # Tabulate aggregate statistics
            agg_trends = trend_func(data_df,trend_vars,'agg_trend')

            all_trends.append(agg_trends)

            # iterate over groupby attributes
            for groupbyAttr in groupby_vars:
                # add groupbyAttr to list of splits
                trend_vars_gb = [tv.append(groupbyAttr) for tv in trend_vars]

                # get subgoup trends
                curgroup_corr = trend_func(cur_grouping,trend_vars_gb,'subgroup_trend')

                # append
                subgroup_trends.append(curgroup_corr)




        # condense and merge all trends with subgroup trends
        all_trends = pd.concat(all_trends)
        subgroup_trends = pd.concat(subgroup_trends)
        result_df = pd.merge(subgroup_trends,all_trends)
        # ,on=['feat1','feat2'], how='left

        return result_df









################################################################################
# helper functions
################################################################################


# Function s
def upper_triangle_element(matrix):
    """
    extract upper triangle elements without diagonal element

    Parameters
    -----------
    matrix : 2d numpy array

    Returns
    --------
    elements : numpy array
               A array has all the values in the upper half of the input matrix

    """
    #upper triangle construction
    tri_upper = np.triu(matrix, k=1)
    num_rows = tri_upper.shape[0]

    #upper triangle element extract
    elements = tri_upper[np.triu_indices(num_rows,k=1)]

    return elements


def upper_triangle_df(matrix):
    """
    extract upper triangle elements without diagonal element and store the element's
    corresponding rows and columns' index information into a dataframe

    Parameters
    -----------
    matrix : 2d numpy array

    Returns
    --------
    result_df : dataframe
        A dataframe stores all the values in the upper half of the input matrix and
    their corresponding rows and columns' index information into a dataframe
    """
    #upper triangle construction
    tri_upper = np.triu(matrix, k=1)
    num_rows = tri_upper.shape[0]

    #upper triangle element extract
    elements = tri_upper[np.triu_indices(num_rows,k=1)]
    location_tuple = np.triu_indices(num_rows,k=1)
    result_df = pd.DataFrame({'value':elements})
    result_df['attr1'] = location_tuple[0]
    result_df['attr2'] = location_tuple[1]

    return result_df

def isReverse(a, b):
    """
    Reversal is the logical opposite of signs matching.

    Parameters
    -----------
    a : number(int or float)
    b : number(int or float)

    Returns
    --------
    boolean value : If True turns, a and b have the reverse sign.
                    If False returns, a and b have the same sign.
    """

    return not (np.sign(a) == np.sign(b))



def detect_simpsons_paradox(data_df,
                            regression_vars=None,
                            groupby_vars=None,type='linreg' ):
    """
    LEGACY
    A detection function which can detect Simpson Paradox happened in the data's
    subgroup.

    Parameters
    -----------
    data_df : DataFrame
        data organized in a pandas dataframe containing both categorical
        and continuous attributes.
    regression_vars : list [None]
        list of continuous attributes by name in dataframe, if None will be
        detected by all float64 type columns in dataframe
    groupby_vars  : list [None]
        list of group by attributes by name in dataframe, if None will be
        detected by all object and int64 type columns in dataframe
    type : {'linreg',} ['linreg']
        default is linreg for backward compatibility


    Returns
    --------
    result_df : dataframe
        a dataframe with columns ['attr1','attr2',...]
                TODO: Clarify the return information

    """
    # if not specified, detect continous attributes and categorical attributes
    # from dataset
    if groupby_vars is None:
        groupbyAttrs = data_df.select_dtypes(include=['object','int64'])
        groupby_vars = list(groupbyAttrs)

    if regression_vars is None:
        continuousAttrs = data_df.select_dtypes(include=['float64'])
        regression_vars = list(continuousAttrs)


    # Compute correaltion matrix for all of the data, then extract the upper
    # triangle of the matrix.
    # Generate the correaltion dataframe by correlation values.
    all_corr = data_df[regression_vars].corr()
    all_corr_df = upper_triangle_df(all_corr)
    all_corr_element = all_corr_df['value'].values

    # Define an empty dataframe for result
    result_df = pd.DataFrame(columns=RESULTS_DF_HEADER)

    # Loop by group-by attributes
    for groupbyAttr in groupby_vars:
        grouped_df_corr = data_df.groupby(groupbyAttr)[regression_vars].corr()
        groupby_value = grouped_df_corr.index.get_level_values(groupbyAttr).unique()

        # Get subgroup correlation
        for subgroup in groupby_value:
            subgroup_corr = grouped_df_corr.loc[subgroup]

            # Extract subgroup
            subgroup_corr_elements = upper_triangle_element(subgroup_corr)

            # Compare the signs of each element in subgroup to the correlation for all of the data
            # Get the index for reverse element
            index_list = [i for i, (a,b) in enumerate(zip(all_corr_element, subgroup_corr_elements)) if isReverse(a, b)]

            # Get reverse elements' correlation values
            reverse_list = [j for i, j in zip(all_corr_element, subgroup_corr_elements) if isReverse(i, j)]

            if reverse_list:
                # Retrieve attribute information from all_corr_df
                all_corr_info = [all_corr_df.loc[i].values for i in index_list]
                temp_df = pd.DataFrame(data=all_corr_info,columns=['agg_trend','feat1','feat2'])

                # # Convert index from float to int
                temp_df.feat1 = temp_df.feat1.astype(int)
                temp_df.feat2 = temp_df.feat2.astype(int)
                # Convert indices to attribute names for readabiity
                temp_df.feat1 = temp_df.feat1.replace({i:a for i, a in
                                            enumerate(regression_vars)})
                temp_df.feat2 = temp_df.feat2.replace({i:a for i, a in
                                            enumerate(regression_vars)})

                temp_df['subgroup_trend'] = reverse_list
                len_list = len(reverse_list)
                # Store group attributes' information
                temp_df['group_feat'] = [groupbyAttr for i in range(len_list)]
                temp_df['subgroup'] = [subgroup for i in range(len_list)]
                result_df = result_df.append(temp_df, ignore_index=True)

    return result_df




# def detect_sp_pandas():
#     total_data = np.asarray([np.sign(many_sp_df_diff.corr().values)]*3).reshape(18,6)
#     A_data = np.sign(many_sp_df_diff.groupby('A').corr().values)
#     sp_mask = total_data*A_data
# sp_idx = np.argwhere(sp_mask<0)
# #     Comput corr, take sign
# # conditionn and compute suc corrs, take sign
# # mutliply two together, all negative arer SP
# # get locations to dtermine laels
#     labels_levels = many_sp_df_diff.groupby('A').corr().index
#     groupByAttr_list = [labels_levels.levels[0][ll] for ll in labels_levels.labels[0]]
#     var_list_dn  = [labels_levels.levels[1][li] for li in labels_levels.labels[1]]
#     var_list_ac = many_sp_df_diff.groupby('A').corr().columns
#     # labels_levels.levels
#     SP_cases = [(groupByAttr_list[r],var_list_dn[r],var_list_ac[c]) for r,c in sp_idx ]
