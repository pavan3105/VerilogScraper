def solution(primary, secondary, operations):
    """
    Data analysis tool that tracks relationships between two datasets.
    
    Args:
        primary: List of integers (primary dataset)
        secondary: List of integers (secondary dataset) 
        operations: List of operations, where each operation is either:
            - [0, index, newValue]: Update secondary[index] = newValue
            - [1, targetSum]: Count pairs (i,j) where primary[i] + secondary[j] = targetSum
    
    Returns:
        List of results for operations of type [1, targetSum]
    """
    # Make a copy of secondary array to avoid modifying the original
    sec_array = secondary[:]
    results = []
    
    for operation in operations:
        if operation[0] == 0:
            # Update operation: [0, index, newValue]
            index = operation[1]
            new_value = operation[2]
            sec_array[index] = new_value
            
        elif operation[0] == 1:
            # Count operation: [1, targetSum]
            target_sum = operation[1]
            count = 0
            
            # Count all pairs (i,j) where primary[i] + secondary[j] = targetSum
            for i in range(len(primary)):
                for j in range(len(sec_array)):
                    if primary[i] + sec_array[j] == target_sum:
                        count += 1
            
            results.append(count)
    
    return results


# Test with the example from the problem
if __name__ == "__main__":
    # Example test case
    primary = [1, 2, 3]
    secondary = [3, 4]
    operations = [[1, 5], [0, 0, 1], [1, 5]]
    
    result = solution(primary, secondary, operations)
    print(f"Result: {result}")
    print(f"Expected: [2, 1]")
    
    # Let's trace through step by step for verification
    print("\nStep-by-step trace:")
    sec_array = secondary[:]
    print(f"Initial: primary = {primary}, secondary = {sec_array}")
    
    # Operation [1, 5] - count pairs that sum to 5
    count1 = 0
    pairs1 = []
    for i in range(len(primary)):
        for j in range(len(sec_array)):
            if primary[i] + sec_array[j] == 5:
                count1 += 1
                pairs1.append((primary[i], sec_array[j]))
    print(f"Operation [1, 5]: Found {count1} pairs: {pairs1}")
    
    # Operation [0, 0, 1] - update secondary[0] = 1
    sec_array[0] = 1
    print(f"Operation [0, 0, 1]: Updated secondary = {sec_array}")
    
    # Operation [1, 5] - count pairs that sum to 5 again
    count2 = 0
    pairs2 = []
    for i in range(len(primary)):
        for j in range(len(sec_array)):
            if primary[i] + sec_array[j] == 5:
                count2 += 1
                pairs2.append((primary[i], sec_array[j]))
    print(f"Operation [1, 5]: Found {count2} pairs: {pairs2}")
    
    print(f"Final result: [{count1}, {count2}]")