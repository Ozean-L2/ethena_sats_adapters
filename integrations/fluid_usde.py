from constants.chains import Chain
from integrations.integration_ids import IntegrationID
from integrations.integration import Integration
from utils.web3_utils import call_with_retry, W3_BY_CHAIN
from utils.fluid import vaultResolver_contract, vaultPositionResolver_contract
from constants.fluid import USDe

# covers all Fluid normal col USDE vaults.
class FluidIntegration(Integration):

    def __init__(self):
        super().__init__(
            IntegrationID.FLUID_USDE,
            21016131,
            Chain.ETHEREUM,
            [],
            20,
            1,
            None,
            None,
        )
        self.blocknumber_to_usdeVaults = {}

    def get_balance(self, user: str, block: int) -> float:
        balance = 0
        try:
            userPositions, vaultEntireDatas = call_with_retry(
                vaultResolver_contract.functions.positionsByUser(user), block
            )
            for i in range(len(userPositions)):
                if (vaultEntireDatas[i][3][8][0] == USDe) and not (vaultEntireDatas[i][1]): # not smart col types
                    balance += userPositions[i][9]
            return balance / 1e18
        except Exception as e:
            return 0

    def get_participants(self, blocks: list[int] | None) -> set[str]:
        participants = []
        current_block = W3_BY_CHAIN[self.chain]["w3"].eth.get_block_number()

        relevant_vaults = self.get_relevant_vaults(current_block)
        relavantUserPositions = []

        try:
            for vault in relevant_vaults:
                relavantUserPositions += call_with_retry(
                    vaultPositionResolver_contract.functions.getAllVaultPositions(
                        vault
                    ),
                    current_block,
                )
            for userPosition in relavantUserPositions:
                owner = userPosition[1]
                if owner not in participants:
                    participants.append(owner)
        except Exception as e:
            print(f"Error: {str(e)}")
        return set(participants)

    def get_relevant_vaults(self, block: int) -> list:
        if block in self.blocknumber_to_usdeVaults:
            return self.blocknumber_to_usdeVaults[block]

        if self.blocknumber_to_usdeVaults != {}:
            totalVaults = call_with_retry(
                vaultResolver_contract.functions.getTotalVaults(), block
            )
            for block_number in self.blocknumber_to_usdeVaults:
                totalVaults_at_block = call_with_retry(
                    vaultResolver_contract.functions.getTotalVaults(), block_number
                )
                if totalVaults == totalVaults_at_block:
                    self.blocknumber_to_usdeVaults[block] = (
                        self.blocknumber_to_usdeVaults[block_number]
                    )
                    return self.blocknumber_to_usdeVaults[block_number]

        vaults = call_with_retry(
            vaultResolver_contract.functions.getAllVaultsAddresses(), block
        )
        relevantVaults = []
        for vaultAddress in vaults:
            vaultData = call_with_retry(
                vaultResolver_contract.functions.getVaultEntireData(vaultAddress), block
            )
            if (vaultData[3][8][0] == USDe) and not (vaultData[1]): # not smart col types
                relevantVaults.append(vaultAddress)
        self.blocknumber_to_usdeVaults[block] = relevantVaults
        return relevantVaults


if __name__ == "__main__":
    example_integration = FluidIntegration()
    current_block = W3_BY_CHAIN[example_integration.chain]["w3"].eth.get_block_number()
    print("getting relevant vaults")
    print(example_integration.get_relevant_vaults(current_block))

    print("\n\n\ngetting participants")
    print(example_integration.get_participants(None))

    print("\n\n\n getting balance")
    print(
        example_integration.get_balance(
            "0xD15B0aA03Bc9F74Aa3d07d078502867Da3B7d198", 21745303
        )
    )
