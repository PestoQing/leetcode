#include <algorithm>
#include <iostream>
#include <limits>
#include <set>
#include <tuple>
#include <utility>
#include <vector>

using namespace std;

int main() {
    vector<pair<int, int>> candidate = {{1, 2}, {2, 1}, {1, 1}, {3, 3}};

    // 每条记录是 (s, c, 原下标)，排序后相同 s 的轨迹会相邻。
    vector<tuple<int, int, int>> nums;
    for (int i = 0; i < static_cast<int>(candidate.size()); i++) {
        nums.emplace_back(candidate[i].first, candidate[i].second, i);
    }
    sort(nums.begin(), nums.end());

    set<int> seen;
    int best = numeric_limits<int>::max();
    int left = 0;

    while (left < static_cast<int>(nums.size())) {
        int min_c = get<1>(nums[left]);
        int cnt = 1;
        int right = left + 1;

        while (right < static_cast<int>(nums.size()) &&
               get<0>(nums[right]) == get<0>(nums[left])) {
            if (get<1>(nums[right]) < min_c) {
                min_c = get<1>(nums[right]);
                cnt = 1;
            } else if (get<1>(nums[right]) == min_c) {
                cnt++;
            }
            right++;
        }

        if (min_c < best) {
            // 同组最小 c 的所有轨迹都保留，并恢复原下标。
            for (int i = left; i < left + cnt; i++) {
                seen.insert(get<2>(nums[i]));
            }
            best = min_c;
        }
        left = right;
    }

    cout << "[";
    bool first = true;
    for (int i = 0; i < static_cast<int>(candidate.size()); i++) {
        if (seen.count(i) == 0) {
            continue;
        }
        if (!first) {
            cout << ", ";
        }
        cout << "[" << candidate[i].first << ", " << candidate[i].second << "]";
        first = false;
    }
    cout << "]\n";

    return 0;
}
