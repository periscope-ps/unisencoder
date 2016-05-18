class Permutation:

    @staticmethod
    def combination_util(arr, data, start, end, index, r, final_list):

        temp_list = []
        if index == r:
            for j in range(0,r):
                temp_list.append(data[j])
                # print(str(data[j])+" ")
            # print("")
            final_list.append(temp_list)
            return

        i=start
        while(i<=end and end-i+1 >= r-index):
            data[index] = arr[i]
            Permutation.combination_util(arr, data, i+1, end, index+1, r, final_list)
            i += 1

    @staticmethod
    def permutation(n, r):
        final_list = []
        arr = []
        for j in range(0,n):
            arr.append(j)

        data = []
        for i in range(r):
            data.append(0)

        Permutation.combination_util(arr, data, 0, n-1, 0, r, final_list)
        return final_list

ret_list = Permutation.permutation(4, 2)