import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("../data/raw/churn.csv")

print(df.head())

print("\nDimensions :")
print(df.shape)

print("\nTypes :")
print(df.dtypes)

print("\nValeurs manquantes :")
print(df.isnull().sum())

print("\nStatistiques :")
print(df.describe())

print("\nRépartition du churn :")
print(df["churn"].value_counts())

sns.countplot(data=df, x="churn")
plt.title("Répartition des clients selon le churn")
plt.savefig("../data/churn_distribution.png")
plt.show()

plt.figure(figsize=(10, 6))
sns.heatmap(df.corr(), annot=True)
plt.title("Corrélations")
plt.savefig("../data/correlation.png")
plt.show()
